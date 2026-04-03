/* ============================================================
   A2A Code Review Pipeline — Frontend Logic
   ============================================================ */

// Raw text storage for copy functionality
let rawData = {
    generated: '',
    review: '',
    refactored: ''
};

// Configure marked.js
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true,
});

/**
 * Set a prompt from example buttons.
 */
function setPrompt(text) {
    document.getElementById('promptInput').value = text;
    document.getElementById('promptInput').focus();
}

/**
 * Switch between result tabs.
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

/**
 * Copy content to clipboard.
 */
async function copyContent(type) {
    const text = rawData[type] || '';
    try {
        await navigator.clipboard.writeText(text);
        // Show brief feedback
        const btn = event.target.closest('.btn');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        btn.style.color = '#10b981';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.color = '';
        }, 1500);
    } catch (err) {
        console.error('Copy failed:', err);
    }
}

/**
 * Animate pipeline step to active state.
 */
function activateStep(stepName) {
    const step = document.getElementById(`step-${stepName}`);
    step.classList.add('active');
    step.classList.remove('completed');

    // Show spinner
    const spinner = document.getElementById(`spinner-${stepName}`);
    if (spinner) {
        spinner.style.display = 'block';
    }

    // Hide checkmark
    const check = document.getElementById(`check-${stepName}`);
    if (check) {
        check.style.display = 'none';
    }
}

/**
 * Animate pipeline step to completed state.
 */
function completeStep(stepName, timeSeconds) {
    const step = document.getElementById(`step-${stepName}`);
    step.classList.remove('active');
    step.classList.add('completed');

    // Hide spinner, show checkmark
    const spinner = document.getElementById(`spinner-${stepName}`);
    if (spinner) {
        spinner.style.display = 'none';
    }

    const check = document.getElementById(`check-${stepName}`);
    if (check) {
        check.style.display = 'block';
    }

    // Show time
    const timeEl = document.getElementById(`time-${stepName}`);
    if (timeEl && timeSeconds !== undefined) {
        timeEl.textContent = `${timeSeconds}s`;
    }
}

/**
 * Reset all pipeline step visuals.
 */
function resetSteps() {
    ['discovery', 'writer', 'reviewer', 'refactorer'].forEach(name => {
        const step = document.getElementById(`step-${name}`);
        if (step) {
            step.classList.remove('active', 'completed');
        }

        const spinner = document.getElementById(`spinner-${name}`);
        if (spinner) {
            spinner.style.display = name === 'discovery' ? 'block' : 'none';
        }

        const check = document.getElementById(`check-${name}`);
        if (check) {
            check.style.display = 'none';
        }

        const timeEl = document.getElementById(`time-${name}`);
        if (timeEl) {
            timeEl.textContent = '';
        }
    });
}

/**
 * Run the full pipeline.
 */
async function runPipeline() {
    const prompt = document.getElementById('promptInput').value.trim();
    if (!prompt) {
        document.getElementById('promptInput').focus();
        return;
    }

    // Disable submit button
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
        <div class="spinner" style="width:16px;height:16px;border-width:2px;"></div>
        Processing...
    `;

    // Show pipeline, hide results/errors
    document.getElementById('pipelineSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';

    // Reset and start animation
    resetSteps();
    activateStep('discovery');

    // Simulate step progression for visual feedback
    // (actual timing comes from the server response)
    const stepTimers = [];
    stepTimers.push(setTimeout(() => {
        completeStep('discovery');
        activateStep('writer');
    }, 2000));

    stepTimers.push(setTimeout(() => {
        completeStep('writer');
        activateStep('reviewer');
    }, 8000));

    stepTimers.push(setTimeout(() => {
        completeStep('reviewer');
        activateStep('refactorer');
    }, 16000));

    try {
        const response = await fetch('/api/pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
        });

        // Clear animation timers
        stepTimers.forEach(t => clearTimeout(t));

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        // Update pipeline steps with real timing
        completeStep('discovery', data.timings?.discovery);
        completeStep('writer', data.timings?.code_generation);
        completeStep('reviewer', data.timings?.code_review);
        completeStep('refactorer', data.timings?.code_refactoring);

        // Store raw data
        rawData.generated = data.generated_code || '';
        rawData.review = data.code_review || '';
        rawData.refactored = data.refactored_code || '';

        // Render markdown content
        document.getElementById('generatedContent').innerHTML = marked.parse(rawData.generated);
        document.getElementById('reviewContent').innerHTML = marked.parse(rawData.review);
        document.getElementById('refactoredContent').innerHTML = marked.parse(rawData.refactored);

        // Apply syntax highlighting
        document.querySelectorAll('.markdown-body pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        // Update stats
        document.getElementById('statTotal').textContent = `${data.timings?.total || '—'}s`;
        document.getElementById('statWriter').textContent = `${data.timings?.code_generation || '—'}s`;
        document.getElementById('statReviewer').textContent = `${data.timings?.code_review || '—'}s`;
        document.getElementById('statRefactorer').textContent = `${data.timings?.code_refactoring || '—'}s`;

        // Show results
        document.getElementById('resultsSection').style.display = 'block';
        switchTab('generated');

        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        // Clear animation timers
        stepTimers.forEach(t => clearTimeout(t));

        // Show error
        document.getElementById('pipelineSection').style.display = 'none';
        document.getElementById('errorSection').style.display = 'block';
        document.getElementById('errorMessage').textContent = error.message;
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            Run Pipeline
        `;
    }
}

/**
 * Reset the pipeline UI.
 */
function resetPipeline() {
    document.getElementById('pipelineSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
    document.getElementById('promptInput').focus();
}

/**
 * Check health of all agents.
 */
async function checkHealth() {
    const modal = document.getElementById('healthModal');
    const content = document.getElementById('healthContent');
    modal.style.display = 'flex';
    content.innerHTML = '<div style="text-align:center;padding:2rem;"><div class="spinner" style="margin:0 auto 1rem;"></div><p style="color:var(--text-secondary);">Checking agents...</p></div>';

    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        let html = '';
        let allOnline = true;

        for (const [key, agent] of Object.entries(data.agents)) {
            const isOnline = agent.status === 'online';
            if (!isOnline) allOnline = false;

            const displayName = agent.name || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            html += `
                <div class="agent-status-item">
                    <div class="agent-status-info">
                        <div>
                            <div class="agent-status-name">${displayName}</div>
                            <div class="agent-status-url">${agent.url}</div>
                        </div>
                    </div>
                    <span class="status-badge ${isOnline ? 'online' : 'offline'}">
                        ${isOnline ? '● Online' : '● Offline'}
                    </span>
                </div>
            `;
        }

        content.innerHTML = html;

        // Update header status dot
        const dot = document.getElementById('statusDot');
        dot.className = `status-dot ${allOnline ? 'online' : 'offline'}`;

    } catch (error) {
        content.innerHTML = `
            <div style="text-align:center;padding:2rem;">
                <p style="color:var(--error);font-weight:600;">Failed to check agents</p>
                <p style="color:var(--text-secondary);font-size:0.85rem;margin-top:0.5rem;">${error.message}</p>
            </div>
        `;
    }
}

/**
 * Close health modal.
 */
function closeHealthModal(event) {
    if (event.target === event.currentTarget) {
        document.getElementById('healthModal').style.display = 'none';
    }
}

/**
 * Keyboard shortcut: Ctrl/Cmd + Enter to run pipeline.
 */
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runPipeline();
    }
});
