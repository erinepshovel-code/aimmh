const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(`${API}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  });

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const detail = data?.detail || data?.message || response.statusText || 'Request failed';
    throw new Error(detail);
  }

  return data;
}

export const hubApi = {
  getModels: () => request('/v1/models'),
  getOptions: () => request('/v1/hub/options'),
  getInstances: (includeArchived = false) => request(`/v1/hub/instances?include_archived=${includeArchived}`),
  createInstance: (payload) => request('/v1/hub/instances', { method: 'POST', body: JSON.stringify(payload) }),
  updateInstance: (instanceId, payload) => request(`/v1/hub/instances/${instanceId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  archiveInstance: (instanceId) => request(`/v1/hub/instances/${instanceId}/archive`, { method: 'POST' }),
  unarchiveInstance: (instanceId) => request(`/v1/hub/instances/${instanceId}/unarchive`, { method: 'POST' }),
  getInstanceHistory: (instanceId, limit = 200) => request(`/v1/hub/instances/${instanceId}/history?limit=${limit}`),
  getGroups: (includeArchived = false) => request(`/v1/hub/groups?include_archived=${includeArchived}`),
  createGroup: (payload) => request('/v1/hub/groups', { method: 'POST', body: JSON.stringify(payload) }),
  updateGroup: (groupId, payload) => request(`/v1/hub/groups/${groupId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  archiveGroup: (groupId) => request(`/v1/hub/groups/${groupId}/archive`, { method: 'POST' }),
  unarchiveGroup: (groupId) => request(`/v1/hub/groups/${groupId}/unarchive`, { method: 'POST' }),
  getRuns: () => request('/v1/hub/runs'),
  getRunDetail: (runId) => request(`/v1/hub/runs/${runId}`),
  createRun: (payload) => request('/v1/hub/runs', { method: 'POST', body: JSON.stringify(payload) }),
};
