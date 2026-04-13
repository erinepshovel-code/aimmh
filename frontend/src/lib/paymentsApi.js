// "lines of code":"49","lines of commented":"0"
import { getTrialGuestId } from './trialSession';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-Guest-Id': getTrialGuestId(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  });

  let text = '';
  try {
    text = await response.text();
  } catch {
    text = '';
  }
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const detail = data?.detail || data?.message || response.statusText || 'Request failed';
    if (typeof detail === 'string' && detail.toLowerCase().includes('daily trial exhausted')) {
      window.location.href = '/auth';
    }
    throw new Error(detail);
  }

  return data;
}

export const paymentsApi = {
  getCatalog: () => request('/payments/catalog'),
  getSummary: () => request('/payments/summary'),
  createCheckout: (packageId, originUrl, customAmount = null) => request('/payments/checkout/session', {
    method: 'POST',
    body: JSON.stringify({
      package_id: packageId,
      origin_url: originUrl,
      ...(typeof customAmount === 'number' && Number.isFinite(customAmount) ? { custom_amount: customAmount } : {}),
    }),
  }),
  getCheckoutStatus: (sessionId) => request(`/payments/checkout/status/${sessionId}`),
  getHall: () => request('/payments/hall-of-makers'),
  updateHallProfile: (payload) => request('/payments/hall-of-makers/profile', { method: 'PUT', body: JSON.stringify(payload) }),
};
// "lines of code":"49","lines of commented":"0"
