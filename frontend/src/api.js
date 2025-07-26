const BASE_URL = import.meta.env.VITE_API_URL;

// Start the pipeline
async function startPipeline(userQuery) {
  console.log(`userQuery: ${userQuery}`);
  const res = await fetch(BASE_URL + '/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_query: userQuery })
  });

  console.log(`Response: ${res}`);
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Pipeline start failed');
  }

  return await res.json();
}

// Poll the pipeline status 
async function getPipelineStatus() {
  const res = await fetch(BASE_URL + '/status');

  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Status fetch failed');
  }

  return await res.json();
}

export default {
  startPipeline,
  getPipelineStatus
};