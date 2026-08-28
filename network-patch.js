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
  const readLiveToken = () => {
    const el = document.querySelector('#token');
    return el && typeof el.value === 'string' ? el.value.trim() : '';
  };
  const buildInit = (input, init = {}, forceLiveToken = false) => {
    const headers = new Headers((input instanceof Request ? input.headers : undefined) || init.headers || {});
    const liveToken = readLiveToken();
    if (liveToken && (forceLiveToken || !headers.has('Authorization'))) {
      headers.set('Authorization', `Bearer ${liveToken}`);
    }
    headers.set('Accept', headers.get('Accept') || 'application/vnd.github+json');
    headers.set('X-GitHub-Api-Version', headers.get('X-GitHub-Api-Version') || '2022-11-28');
    return {...init, headers};
  };

  async function resilientFetch(input, init = {}) {
    if (!isGithub(input)) return nativeFetch(input, init);

    const method = String(init.method || (input && input.method) || 'GET').toUpperCase();
    const maxAttempts = method === 'PUT' ? 7 : 5;
    let lastError;
    let requestInit = buildInit(input, init, false);
    let authRefreshUsed = false;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        let response = await nativeFetch(input, requestInit);

        if (response.status === 401 && !authRefreshUsed) {
          const liveToken = readLiveToken();
          if (liveToken) {
            authRefreshUsed = true;
            requestInit = buildInit(input, init, true);
            console.warn('[Project Strike] GitHub returned 401; refreshing Authorization from the current token field and retrying once.');
            await sleep(250);
            response = await nativeFetch(input, requestInit);
          }
        }

        if (response.status === 401) {
          console.error('[Project Strike] GitHub authentication rejected. The token is invalid, expired, revoked, or does not have access to this repository.');
          return response;
        }

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
  console.info('[Project Strike] resilient GitHub upload transport + live auth repair enabled');
})();
