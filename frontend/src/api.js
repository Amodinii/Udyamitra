const BASE_URL = import.meta.env.VITE_API_URL;

// Call to /intent
async function getIntent(userQuery) {
  const res = await fetch(BASE_URL + '/intent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_query: userQuery })
  });

  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Intent fetch failed');
  }

  return await res.json();
}

// Call to /run
async function runTool({ user_query, user_inputs, tool_name, server_path, server_sources }) {
  const res = await fetch(BASE_URL + '/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_query,
      user_inputs,
      tool_name,
      server_path,
      server_sources
    })
  });

  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Tool run failed');
  }

  return await res.json();
}

export default {
  getIntent,
  runTool
};