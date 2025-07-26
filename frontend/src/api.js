const BASE_URL = import.meta.env.VITE_API_URL;

// Start the pipeline
async function startPipeline(userQuery) {
  console.log(`userQuery: ${userQuery}`);
  const res = await fetch(BASE_URL + '/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_query: userQuery })
  });

  const data = await res.json(); // Read JSON once

  if (!res.ok) {
    throw new Error(data.detail || 'Pipeline start failed');
  }

  console.log(data); // Log parsed JSON
  return data;
}

// Poll the pipeline status 
async function getPipelineStatus() {
  const res = await fetch(BASE_URL + '/status');

  const data = await res.json(); // Read JSON once

  if (!res.ok) {
    throw new Error(data.detail || 'Status fetch failed');
  }

  console.log(data); // Log parsed JSON
  return data;
}

export default {
  startPipeline,
  getPipelineStatus
};
