const TRIAL_GUEST_KEY = 'aimmh-trial-guest-id';
const TRIAL_GUEST_DAY_KEY = 'aimmh-trial-guest-day';

function todayUtcKey() {
  return new Date().toISOString().slice(0, 10);
}

function randomGuestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `guest-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

export function getTrialGuestId() {
  const day = todayUtcKey();
  const storedDay = localStorage.getItem(TRIAL_GUEST_DAY_KEY);
  const storedId = localStorage.getItem(TRIAL_GUEST_KEY);
  if (storedId && storedDay === day) return storedId;
  const nextId = randomGuestId();
  localStorage.setItem(TRIAL_GUEST_KEY, nextId);
  localStorage.setItem(TRIAL_GUEST_DAY_KEY, day);
  return nextId;
}
