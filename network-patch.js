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
  const tokenField = () => document.querySelector('#token');
  const readLiveToken = () => {
    const el = tokenField();
    return el && typeof el.value === 'string' ? el.value.trim() : '';
  };
  const writeLiveToken = token => {
    const el = tokenField();
    if (el) {
      el.value = String(token || '').trim();
      el.dispatchEvent(new Event('input', {bubbles:true}));
      el.dispatchEvent(new Event('change', {bubbles:true}));
    }
  };
  const authHeaders = (input, init = {}, forceToken = '') => {
    const headers = new Headers((input instanceof Request ? input.headers : undefined) || init.headers || {});
    const token = String(forceToken || readLiveToken()).trim();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    headers.set('Accept', headers.get('Accept') || 'application/vnd.github+json');
    headers.set('X-GitHub-Api-Version', headers.get('X-GitHub-Api-Version') || '2022-11-28');
    return {...init, headers};
  };
  const explain401 = () => {
    const status = document.querySelector('#status');
    if (status) {
      status.className = 'status bad';
      status.textContent = 'GitHub rejected the current token (401). Paste a fresh fine-grained token with Contents: Read and write. The current upload will resume from the failed request instead of restarting.';
    }
  };

  async function resilientFetch(input, init = {}) {
    if (!isGithub(input)) return nativeFetch(input, init);

    const method = String(init.method || (input && input.method) || 'GET').toUpperCase();
    const maxAttempts = method === 'PUT' ? 7 : 5;
    let lastError;
    let requestInit = authHeaders(input, init);
    let replacementPromptUsed = false;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        let response = await nativeFetch(input, requestInit);

        if (response.status === 401) {
          explain401();
          console.error('[Project Strike] GitHub rejected the current credential with 401 Bad credentials.');

          if (!replacementPromptUsed) {
            replacementPromptUsed = true;
            const current = readLiveToken();
            let replacement = '';
            try {
              replacement = window.prompt(
                'GitHub rejected the current token. Paste a fresh fine-grained GitHub token with Contents: Read and write to resume this exact upload request. Cancel to stop.',
                ''
              ) || '';
            } catch {}
            replacement = replacement.trim();

            if (replacement && replacement !== current) {
              writeLiveToken(replacement);
              requestInit = authHeaders(input, init, replacement);
              console.warn('[Project Strike] New GitHub credential supplied; retrying the failed request without restarting the asset batch.');
              await sleep(250);
              response = await nativeFetch(input, requestInit);
            }
          }
        }

        if (response.status === 401) return response;
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
  console.info('[Project Strike] resilient GitHub transport enabled: live auth, 401 recovery, in-place resume, and transient retry support.');
})();