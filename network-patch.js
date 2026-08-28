(()=>{
  if (window.__PROJECT_STRIKE_NETWORK_PATCH__) return;
  window.__PROJECT_STRIKE_NETWORK_PATCH__ = true;

  const nativeFetch = window.fetch.bind(window);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const transientStatus = s => s === 408 || s === 409 || s === 425 || s === 429 || (s >= 500 && s <= 599);
  const isGithub = input => {
    const u = typeof input === 'string' ? input : (input && input.url) || '';
    return /^https:\/\/api\.github\.com\//i.test(u);
  };

  async function resilientFetch(input, init = {}) {
    if (!isGithub(input)) return nativeFetch(input, init);

    const method = String(init.method || (input && input.method) || 'GET').toUpperCase();
    const maxAttempts = method === 'PUT' ? 7 : 5;
    let lastError;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await nativeFetch(input, init);
        if (!transientStatus(response.status) || attempt === maxAttempts) return response;
        const retryAfter = Number(response.headers.get('retry-after')) || 0;
        await sleep(Math.max(retryAfter * 1000, Math.min(8000, 450 * (2 ** (attempt - 1)) + Math.random() * 300)));
      } catch (error) {
        lastError = error;
        if (attempt === maxAttempts) throw error;
        const msg = String(error && (error.message || error));
        console.warn(`[Project Strike] GitHub ${method} network retry ${attempt}/${maxAttempts}: ${msg}`);
        if (navigator.onLine === false) {
          await new Promise(resolve => {
            const done = () => { window.removeEventListener('online', done); resolve(); };
            window.addEventListener('online', done, { once: true });
            setTimeout(done, 12000);
          });
        } else {
          await sleep(Math.min(9000, 650 * (2 ** (attempt - 1)) + Math.random() * 400));
        }
      }
    }
    throw lastError || new Error('GitHub request failed after retries');
  }

  window.fetch = resilientFetch;
  console.info('[Project Strike] resilient GitHub upload transport enabled');
})();
