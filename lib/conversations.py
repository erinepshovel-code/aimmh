"""
conversations.py — Async multi-model conversation orchestration primitives.

All functions are pure async — no FastAPI, MongoDB, auth, or framework deps.
The only dependency is Python stdlib + asyncio.

The core insight: async is the library's reason for being. fan_out uses
asyncio.gather for true parallel calls; sequential patterns (daisy_chain,
roleplay) use await so each step can depend on the last. Callers compose
these freely without the backend's HTTP/DB overhead.

CallFn contract: async (model_id: str, messages: list[dict]) -> str
  - messages follows the OpenAI role format: [{"role": "user"|"assistant"|"system", "content": str}]
  - returns the full response string (adapters handle streaming → complete)
  - on error, returns a string starting with "[ERROR]"
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Optional

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

# async fn(model_id, messages) -> complete response string
CallFn = Callable[[str, list[dict]], Coroutine[None, None, str]]


@dataclass
class ModelResult:
    """A single model response within a conversation pattern.

    step_num=-1 is a sentinel for synthesis/DM steps that sit between rounds.
    Filter helpers:
        responses only:   [r for r in results if r.step_num >= 0]
        synthesis/DM:     [r for r in results if r.step_num == -1]
        by round:         [r for r in results if r.round_num == n]
    """
    model: str
    content: str
    response_time_ms: int = 0
    error: Optional[str] = None
    round_num: int = 0       # 0-indexed round
    step_num: int = 0        # 0-indexed step within round; -1 = synthesis/DM narration
    initiative: int = 0      # initiative roll (roleplay); 0 for non-roleplay patterns
    role: str = "player"     # "player" | "dm" | "synthesizer" | "council"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _inject_system(
    messages: list[dict],
    model_id: str,
    per_model_system: Optional[dict[str, str]],
) -> list[dict]:
    """Prepend {"role": "system", "content": ...} if per_model_system has an entry."""
    if not per_model_system or model_id not in per_model_system:
        return messages
    return [{"role": "system", "content": per_model_system[model_id]}] + messages


def _trim(history: list[dict], max_history: int) -> list[dict]:
    """Keep the last max_history messages (pairs = 2 items each)."""
    return history[-max_history:] if len(history) > max_history else history


async def _call(
    call: CallFn,
    model_id: str,
    messages: list[dict],
    per_model_system: Optional[dict[str, str]],
    round_num: int,
    step_num: int,
    role: str = "player",
    initiative: int = 0,
) -> ModelResult:
    """Single timed call with error capture."""
    msgs = _inject_system(messages, model_id, per_model_system)
    t = time.monotonic()
    try:
        content = await call(model_id, msgs)
    except Exception as e:
        content = f"[ERROR] {e}"
    elapsed_ms = int((time.monotonic() - t) * 1000)
    return ModelResult(
        model=model_id,
        content=content,
        response_time_ms=elapsed_ms,
        error=content if content.startswith("[ERROR]") else None,
        round_num=round_num,
        step_num=step_num,
        initiative=initiative,
        role=role,
    )


# ---------------------------------------------------------------------------
# fan_out — parallel building block
# ---------------------------------------------------------------------------

async def fan_out(
    call: CallFn,
    model_ids: list[str],
    messages: list[dict],
    per_model_system: Optional[dict[str, str]] = None,
    round_num: int = 0,
    step_num: int = 0,
) -> list[ModelResult]:
    """Call all models in parallel with the same messages.

    This is the async core: asyncio.gather fires all calls concurrently.
    Returns results in model_ids order.
    """
    return list(await asyncio.gather(*[
        _call(call, m, messages, per_model_system, round_num, step_num)
        for m in model_ids
    ]))


# ---------------------------------------------------------------------------
# daisy_chain — sequential A → B → C
# ---------------------------------------------------------------------------

async def daisy_chain(
    call: CallFn,
    model_ids: list[str],
    prompt: str,
    rounds: int = 1,
    per_model_system: Optional[dict[str, str]] = None,
    include_original_prompt: bool = True,
    max_history: int = 30,
) -> list[ModelResult]:
    """Sequential chain: each model's response becomes the next model's prompt.

    Round 0, step 0: raw prompt → model[0].
    All subsequent steps:
        [Chain Round {r+1}, Step {s+1}]
        Previous response from {prev_model}: {content}
        Original prompt: {prompt}   ← if include_original_prompt

    History accumulates so each step has full prior context.
    """
    all_results: list[ModelResult] = []
    history: list[dict] = []
    last_content = prompt
    last_model = "user"

    for round_num in range(rounds):
        for step_num, model_id in enumerate(model_ids):
            if round_num == 0 and step_num == 0:
                prompt_text = prompt
            else:
                prompt_text = (
                    f"[Chain Round {round_num + 1}, Step {step_num + 1}]\n\n"
                    f"Previous response from {last_model}:\n{last_content}"
                )
                if include_original_prompt:
                    prompt_text += f"\n\nOriginal prompt: {prompt}"

            messages = _trim(history, max_history) + [{"role": "user", "content": prompt_text}]
            result = await _call(call, model_id, messages, per_model_system, round_num, step_num)
            all_results.append(result)

            history.append({"role": "user", "content": prompt_text})
            history.append({"role": "assistant", "content": result.content})
            last_content = result.content
            last_model = model_id

    return all_results


# ---------------------------------------------------------------------------
# room_all — every model sees all others' responses
# ---------------------------------------------------------------------------

async def room_all(
    call: CallFn,
    model_ids: list[str],
    prompt: str,
    rounds: int = 1,
    per_model_system: Optional[dict[str, str]] = None,
    max_history: int = 30,
) -> list[ModelResult]:
    """Shared room: all models respond, then each sees all responses, responds again.

    Round 0: parallel fan_out with raw prompt.
    Round 1+: each model receives:
        [ROUND {r+1} — respond after seeing other models' responses]
        Response from {model_a}: {content}
        ---
        Response from {model_b}: {content}
        Original prompt: {prompt}

    Single shared history (all models in the same room context).
    """
    all_results: list[ModelResult] = []
    shared_history: list[dict] = []

    for round_num in range(rounds):
        if round_num == 0:
            user_turn = {"role": "user", "content": prompt}
            messages = _trim(shared_history, max_history) + [user_turn]
            round_results = await fan_out(call, model_ids, messages, per_model_system, round_num=0)
        else:
            prev_round = all_results[-(len(model_ids)):]
            share_text = f"[ROUND {round_num + 1} — respond after seeing other models' responses]\n\n"
            share_text += "\n\n---\n\n".join(
                f"Response from {r.model}:\n{r.content}"
                for r in prev_round if not r.error
            )
            share_text += f"\n\nOriginal prompt: {prompt}"

            user_turn = {"role": "user", "content": share_text}
            messages = _trim(shared_history, max_history) + [user_turn]
            round_results = list(await asyncio.gather(*[
                _call(call, m, messages, per_model_system, round_num, step_num=0)
                for m in model_ids
            ]))

        all_results.extend(round_results)

        # Shared history: one user turn + all assistant responses
        shared_history.append(user_turn)
        for r in round_results:
            shared_history.append({"role": "assistant", "content": r.content})

    return all_results


# ---------------------------------------------------------------------------
# room_synthesized — one synthesizer combines responses, drives next round
# ---------------------------------------------------------------------------

async def room_synthesized(
    call: CallFn,
    model_ids: list[str],
    prompt: str,
    synthesis_model: str,
    rounds: int = 1,
    synthesis_prompt: str = "Synthesize and analyze these AI responses:",
    per_model_system: Optional[dict[str, str]] = None,
    max_history: int = 30,
) -> list[ModelResult]:
    """All models respond in parallel; one synthesis model combines them.

    Round 0: parallel fan_out.
    Synthesis (step_num=-1): synthesis_model receives:
        [ROUND {r+1} SYNTHESIS]
        {synthesis_prompt}
        Response from {model_a}: {content}
        ---
        Response from {model_b}: {content}
    Round 1+: models respond to synthesis:
        [ROUND {r+1} — respond to the synthesis]
        Synthesis by {synthesis_model}: {synth_content}
        Original prompt: {prompt}

    synthesis_model results have step_num=-1.
    Filter: [r for r in results if r.step_num >= 0] → player responses only.
    """
    if not synthesis_model:
        raise ValueError("synthesis_model is required")

    all_results: list[ModelResult] = []
    shared_history: list[dict] = []

    for round_num in range(rounds):
        # --- player round ---
        if round_num == 0:
            user_turn = {"role": "user", "content": prompt}
        else:
            prev_synth = next(
                (r for r in reversed(all_results) if r.step_num == -1), None
            )
            next_prompt = (
                f"[ROUND {round_num + 1} — respond to the synthesis]\n\n"
                f"Synthesis by {synthesis_model}:\n{prev_synth.content}\n\n"
                f"Original prompt: {prompt}"
            ) if prev_synth else prompt
            user_turn = {"role": "user", "content": next_prompt}

        messages = _trim(shared_history, max_history) + [user_turn]
        round_results = list(await asyncio.gather(*[
            _call(call, m, messages, per_model_system, round_num, step_num=0, role="player")
            for m in model_ids
        ]))
        all_results.extend(round_results)
        shared_history.append(user_turn)
        for r in round_results:
            shared_history.append({"role": "assistant", "content": r.content})

        # --- synthesis step ---
        synth_input = "\n\n---\n\n".join(
            f"Response from {r.model}:\n{r.content}"
            for r in round_results if not r.error
        )
        synth_turn = {"role": "user", "content": (
            f"[ROUND {round_num + 1} SYNTHESIS]\n"
            f"{synthesis_prompt}\n\n{synth_input}"
        )}
        synth_messages = _trim(shared_history, max_history) + [synth_turn]
        synth_result = await _call(
            call, synthesis_model, synth_messages, per_model_system,
            round_num, step_num=-1, role="synthesizer"
        )
        all_results.append(synth_result)
        shared_history.append(synth_turn)
        shared_history.append({"role": "assistant", "content": synth_result.content})

    return all_results


# ---------------------------------------------------------------------------
# council — every model synthesizes all responses (including its own)
# ---------------------------------------------------------------------------

async def council(
    call: CallFn,
    model_ids: list[str],
    prompt: str,
    rounds: int = 1,
    synthesis_prompt: str = "Synthesize and analyze all model responses including your own:",
    per_model_system: Optional[dict[str, str]] = None,
    max_history: int = 30,
) -> list[ModelResult]:
    """Each model produces its own synthesis of all responses in parallel.

    Round 0 (step_num=0): parallel fan_out with raw prompt.
    Synthesis round (step_num=1): each model receives ALL round responses
        (including its own) and synthesizes them concurrently:
        [COUNCIL SYNTHESIS — ROUND {r+1}]
        {synthesis_prompt}
        Response from {model_a}: {content}
        ---
        Response from {model_b}: {content}
    Round 1+ uses prior synthesis outputs as context.

    step_num=0 → initial responses; step_num=1 → synthesis responses.
    """
    all_results: list[ModelResult] = []
    shared_history: list[dict] = []

    for round_num in range(rounds):
        # --- initial responses ---
        if round_num == 0:
            user_turn = {"role": "user", "content": prompt}
        else:
            prev_syntheses = [
                r for r in all_results
                if r.round_num == round_num - 1 and r.step_num == 1
            ]
            council_context = "\n\n---\n\n".join(
                f"Synthesis by {r.model}:\n{r.content}"
                for r in prev_syntheses if not r.error
            )
            user_turn = {"role": "user", "content": (
                f"[COUNCIL ROUND {round_num + 1}]\n\n"
                f"Prior syntheses:\n\n{council_context}\n\n"
                f"Original prompt: {prompt}"
            )}

        messages = _trim(shared_history, max_history) + [user_turn]
        round_results = list(await asyncio.gather(*[
            _call(call, m, messages, per_model_system, round_num, step_num=0, role="council")
            for m in model_ids
        ]))
        all_results.extend(round_results)
        shared_history.append(user_turn)
        for r in round_results:
            shared_history.append({"role": "assistant", "content": r.content})

        # --- each model synthesizes all responses in parallel ---
        all_responses_text = "\n\n---\n\n".join(
            f"Response from {r.model}:\n{r.content}"
            for r in round_results if not r.error
        )
        synth_turn = {"role": "user", "content": (
            f"[COUNCIL SYNTHESIS — ROUND {round_num + 1}]\n"
            f"{synthesis_prompt}\n\n{all_responses_text}"
        )}
        synth_messages = _trim(shared_history, max_history) + [synth_turn]

        # All models synthesize concurrently — this is the async payoff
        synth_results = list(await asyncio.gather(*[
            _call(call, m, synth_messages, per_model_system, round_num, step_num=1, role="council")
            for m in model_ids
        ]))
        all_results.extend(synth_results)
        shared_history.append(synth_turn)
        for r in synth_results:
            shared_history.append({"role": "assistant", "content": r.content})

    return all_results


# ---------------------------------------------------------------------------
# roleplay — DM narrates, players act in initiative order, reactions supported
# ---------------------------------------------------------------------------

async def roleplay(
    call: CallFn,
    player_models: list[str],
    initial_prompt: str,
    dm_model: Optional[str] = None,
    dm_rotation: Optional[list[str]] = None,
    rounds: int = 1,
    per_model_system: Optional[dict[str, str]] = None,
    action_word_limit: Optional[int] = None,
    use_initiative: bool = True,
    allow_reactions: bool = False,
    max_history: int = 30,
) -> list[ModelResult]:
    """DM-driven roleplay: initiative ordering, sequential player turns, optional reactions.

    Structure per round:
      1. Initiative roll (random) determines player turn order for this round.
      2. Players act sequentially in initiative order. Each player sees:
           - DM's narration from the prior round (or initial_prompt for round 0)
           - Actions of players who have already acted this round
      3. If allow_reactions=True: after each player acts, remaining players
           may react (a brief interrupt response) before the next player goes.
      4. DM sees all player actions → narrates outcome (step_num=-1).
         DM narration drives the next round.

    DM selection:
      - dm_model: fixed DM for all rounds
      - dm_rotation: list of model IDs that cycle as DM each round
      - If neither, the first player_model acts as DM each round

    action_word_limit: injects "Respond in {N} words or fewer." into each
        player's prompt (token economy, like action economy in TTRPGs).

    Returns all ModelResult objects. Use role field to filter:
        players:   [r for r in results if r.role == "player"]
        dm turns:  [r for r in results if r.role == "dm"]
        reactions: [r for r in results if r.role == "reaction"]
    """
    if dm_rotation and dm_model:
        raise ValueError("Provide dm_model or dm_rotation, not both")

    all_results: list[ModelResult] = []
    shared_history: list[dict] = []
    dm_narration = initial_prompt  # seeds round 0

    def _get_dm(round_num: int) -> str:
        if dm_rotation:
            return dm_rotation[round_num % len(dm_rotation)]
        if dm_model:
            return dm_model
        return player_models[0]

    def _active_players(round_num: int) -> list[str]:
        """Players are all models except the DM for this round."""
        dm = _get_dm(round_num)
        return [m for m in player_models if m != dm]

    def _word_limit_suffix() -> str:
        if action_word_limit:
            return f"\n\nRespond in {action_word_limit} words or fewer."
        return ""

    for round_num in range(rounds):
        dm = _get_dm(round_num)
        players = _active_players(round_num)

        # --- initiative: random roll per player, descending order ---
        if use_initiative:
            rolls = {p: random.randint(1, 20) for p in players}
            ordered_players = sorted(players, key=lambda p: rolls[p], reverse=True)
        else:
            rolls = {p: 0 for p in players}
            ordered_players = players

        round_actions: list[ModelResult] = []

        # --- sequential player turns in initiative order ---
        for step_num, player in enumerate(ordered_players):
            # Build context: DM narration + prior player actions this round
            prior_actions = "\n\n".join(
                f"{r.model} acted:\n{r.content}"
                for r in round_actions if not r.error
            )
            if round_actions:
                player_prompt = (
                    f"[ROUND {round_num + 1} — your turn (initiative {rolls[player]})]\n\n"
                    f"DM: {dm_narration}\n\n"
                    f"Actions so far this round:\n{prior_actions}"
                    f"{_word_limit_suffix()}"
                )
            else:
                player_prompt = (
                    f"[ROUND {round_num + 1} — your turn (initiative {rolls[player]}, going first)]\n\n"
                    f"DM: {dm_narration}"
                    f"{_word_limit_suffix()}"
                )

            messages = _trim(shared_history, max_history) + [
                {"role": "user", "content": player_prompt}
            ]
            result = await _call(
                call, player, messages, per_model_system,
                round_num, step_num, role="player", initiative=rolls[player]
            )
            round_actions.append(result)
            all_results.append(result)

            # Update shared history with this player's action
            shared_history.append({"role": "user", "content": player_prompt})
            shared_history.append({"role": "assistant", "content": result.content})

            # --- reactions: remaining players can react to this action ---
            if allow_reactions and not result.error:
                remaining = [p for p in ordered_players if p not in [r.model for r in round_actions]]
                if remaining:
                    reaction_prompt = (
                        f"[ROUND {round_num + 1} — REACTION to {player}'s action]\n\n"
                        f"{player} acted: {result.content}\n\n"
                        f"Do you wish to react? If so, describe your reaction briefly."
                        f"{_word_limit_suffix()}"
                    )
                    reaction_messages = _trim(shared_history, max_history) + [
                        {"role": "user", "content": reaction_prompt}
                    ]
                    # Reactions are parallel among remaining players
                    reactions = list(await asyncio.gather(*[
                        _call(
                            call, p, reaction_messages, per_model_system,
                            round_num, step_num=step_num, role="reaction",
                            initiative=rolls.get(p, 0)
                        )
                        for p in remaining
                    ]))
                    all_results.extend(reactions)
                    # Reactions go into history so DM sees them
                    shared_history.append({"role": "user", "content": reaction_prompt})
                    for rx in reactions:
                        shared_history.append({"role": "assistant", "content": rx.content})

        # --- DM narrates outcome (step_num=-1) ---
        all_actions_text = "\n\n".join(
            f"{r.model} (initiative {r.initiative}): {r.content}"
            for r in round_actions if not r.error
        )
        reactions_this_round = [r for r in all_results if r.round_num == round_num and r.role == "reaction"]
        reactions_text = ""
        if reactions_this_round:
            reactions_text = "\n\nReactions:\n" + "\n\n".join(
                f"{r.model} reacted: {r.content}"
                for r in reactions_this_round if not r.error
            )

        dm_prompt = (
            f"[ROUND {round_num + 1} — DM NARRATION]\n\n"
            f"Player actions this round:\n{all_actions_text}"
            f"{reactions_text}\n\n"
            f"Narrate the outcome and set up the next scene."
        )
        dm_messages = _trim(shared_history, max_history) + [
            {"role": "user", "content": dm_prompt}
        ]
        dm_result = await _call(
            call, dm, dm_messages, per_model_system,
            round_num, step_num=-1, role="dm"
        )
        all_results.append(dm_result)
        shared_history.append({"role": "user", "content": dm_prompt})
        shared_history.append({"role": "assistant", "content": dm_result.content})
        dm_narration = dm_result.content  # seeds next round

    return all_results
