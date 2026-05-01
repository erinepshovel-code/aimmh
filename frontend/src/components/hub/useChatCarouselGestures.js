// "lines of code":"92","lines of commented":"0"
import React from 'react';

function getDistance(touches) {
  if (touches.length < 2) return 0;
  const [a, b] = touches;
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

function getCenter(touches) {
  if (touches.length < 2) return { x: 0, y: 0 };
  const [a, b] = touches;
  return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 };
}

export function useChatCarouselGestures({
  onPrevPrompt,
  onNextPrompt,
  onPrevResponse,
  onNextResponse,
  onLockCurrent,
  setFontScale,
}) {
  const gestureRef = React.useRef({
    touchCount: 0,
    startX: 0,
    startY: 0,
    startDistance: 0,
    startCenterX: 0,
    promptMoved: false,
    lastTapAt: 0,
  });

  const resetGesture = React.useCallback(() => {
    gestureRef.current = { touchCount: 0, startX: 0, startY: 0, startDistance: 0, startCenterX: 0, promptMoved: false, lastTapAt: gestureRef.current.lastTapAt };
  }, []);

  const onTouchStart = React.useCallback((event) => {
    const touches = event.touches;
    if (touches.length === 1) {
      gestureRef.current.touchCount = 1;
      gestureRef.current.startX = touches[0].clientX;
      gestureRef.current.startY = touches[0].clientY;
      return;
    }
    if (touches.length === 2) {
      const center = getCenter(touches);
      gestureRef.current.touchCount = 2;
      gestureRef.current.startDistance = getDistance(touches);
      gestureRef.current.startCenterX = center.x;
      gestureRef.current.promptMoved = false;
    }
  }, []);

  const onTouchMove = React.useCallback((event) => {
    if (gestureRef.current.touchCount !== 2 || event.touches.length < 2) return;
    event.preventDefault();
    const nextDistance = getDistance(event.touches);
    const pinchDelta = nextDistance - gestureRef.current.startDistance;
    if (Math.abs(pinchDelta) > 14) {
      setFontScale((prev) => Math.max(0.8, Math.min(1.8, Number((prev + (pinchDelta > 0 ? 0.05 : -0.05)).toFixed(2)))));
      gestureRef.current.startDistance = nextDistance;
    }
    const center = getCenter(event.touches);
    const centerDeltaX = center.x - gestureRef.current.startCenterX;
    if (!gestureRef.current.promptMoved && Math.abs(centerDeltaX) > 70) {
      if (centerDeltaX < 0) onNextPrompt();
      else onPrevPrompt();
      gestureRef.current.promptMoved = true;
      window.setTimeout(() => {
        gestureRef.current.promptMoved = false;
      }, 240);
      gestureRef.current.startCenterX = center.x;
    }
  }, [onNextPrompt, onPrevPrompt, setFontScale]);

  const onTouchEnd = React.useCallback((event) => {
    if (gestureRef.current.touchCount === 1 && event.changedTouches?.[0]) {
      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - gestureRef.current.startX;
      const deltaY = touch.clientY - gestureRef.current.startY;
      if (Math.abs(deltaX) > 55 && Math.abs(deltaX) > Math.abs(deltaY)) {
        if (deltaX < 0) onNextResponse();
        else onPrevResponse();
      } else {
        const now = Date.now();
        if (now - gestureRef.current.lastTapAt < 280) onLockCurrent();
        gestureRef.current.lastTapAt = now;
      }
    }
    resetGesture();
  }, [onLockCurrent, onNextResponse, onPrevResponse, resetGesture]);

  return { onTouchStart, onTouchMove, onTouchEnd, onTouchCancel: onTouchEnd };
}

// "lines of code":"92","lines of commented":"0"
