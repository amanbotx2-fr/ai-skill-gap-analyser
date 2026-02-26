/* ─────────────────────────────────────────────
   EduPilot AI — Frontend Logic
   ───────────────────────────────────────────── */

const ROADMAP_API_URL = 'http://127.0.0.1:8000/generate-roadmap';
const STORAGE_KEY = 'edupilot-progress';
const ROADMAP_KEY = 'edupilot-roadmap';
const META_KEY = 'edupilot-meta';   // stores exam_name etc.

document.addEventListener('DOMContentLoaded', () => {

    // ── DOM refs ─────────────────────────────────
    const onboardingView = document.getElementById('onboarding-view');
    const dashboardView = document.getElementById('dashboard-view');

    // ─────────────────────────────────────────────
    // ONBOARDING — Step Navigation
    // ─────────────────────────────────────────────

    const steps = document.querySelectorAll('.step');

    function showStep(n) {
        steps.forEach(s => {
            s.classList.toggle('active', Number(s.dataset.step) === n);
        });
    }

    // Next buttons
    document.querySelectorAll('.next-btn[data-next]').forEach(btn => {
        btn.addEventListener('click', () => {
            const currentStep = Number(btn.closest('.step').dataset.step);
            const input = btn.closest('.step').querySelector('input, textarea');
            if (input && !input.value.trim()) {
                input.focus();
                return;
            }
            showStep(Number(btn.dataset.next));
        });
    });

    // Back buttons
    document.querySelectorAll('.back-btn[data-back]').forEach(btn => {
        btn.addEventListener('click', () => {
            showStep(Number(btn.dataset.back));
        });
    });

    // Generate button (final step)
    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', async () => {
            const hoursInput = document.getElementById('hours_per_day');
            if (!hoursInput.value.trim()) { hoursInput.focus(); return; }

            const examName = document.getElementById('exam_name').value.trim();
            const payload = {
                syllabus_text: document.getElementById('syllabus_text').value,
                exam_date: document.getElementById('exam_date').value,
                hours_per_day: Number(hoursInput.value)
            };

            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';

            try {
                const res = await fetch(ROADMAP_API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error('Request failed');

                const data = await res.json();

                // Persist
                localStorage.removeItem(STORAGE_KEY);
                localStorage.setItem(ROADMAP_KEY, JSON.stringify(data));
                localStorage.setItem(META_KEY, JSON.stringify({ exam_name: examName }));

                // Switch to dashboard
                switchToDashboard(data, examName);

            } catch (e) {
                console.error('Roadmap error:', e);
                alert('Unable to generate roadmap. Please ensure the backend server is running.');
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate Roadmap →';
            }
        });
    }

    // New Plan button
    const newPlanBtn = document.getElementById('new-plan-btn');
    if (newPlanBtn) {
        newPlanBtn.addEventListener('click', () => {
            localStorage.removeItem(ROADMAP_KEY);
            localStorage.removeItem(STORAGE_KEY);
            localStorage.removeItem(META_KEY);
            dashboardView.classList.add('hidden');
            onboardingView.classList.remove('hidden');
            showStep(1);
        });
    }

    // ─────────────────────────────────────────────
    // VIEW TOGGLE
    // ─────────────────────────────────────────────

    function switchToDashboard(data, examName) {
        onboardingView.classList.add('hidden');
        dashboardView.classList.remove('hidden');
        renderDashboard(data, examName);
    }

    // ─────────────────────────────────────────────
    // RENDER DASHBOARD
    // ─────────────────────────────────────────────

    function renderDashboard(data, examName) {
        // Title
        const titleEl = document.getElementById('roadmap-title');
        if (titleEl) titleEl.textContent = examName || 'Your Study Roadmap';

        // Strategy Insight
        const stratCard = document.getElementById('strategy-card');
        const stratText = document.getElementById('strategy-text');
        if (stratCard && stratText && data.strategy_insight) {
            stratText.textContent = data.strategy_insight;
            stratCard.classList.remove('hidden');
        }

        // Burnout Risk
        const riskPanel = document.getElementById('risk-card-panel');
        const riskValue = document.getElementById('risk-value');
        if (riskPanel && riskValue && data.burnout_risk) {
            riskValue.textContent = data.burnout_risk;
            riskValue.className = 'risk-badge';
            const cls = { Low: 'risk-low', Medium: 'risk-medium', High: 'risk-high' };
            riskValue.classList.add(cls[data.burnout_risk] || 'risk-medium');
            riskPanel.classList.remove('hidden');
        }

        // Mentor Advice
        const advPanel = document.getElementById('advice-card-panel');
        const mentorTxt = document.getElementById('mentor-text');
        if (advPanel && mentorTxt && data.mentor_advice) {
            mentorTxt.textContent = data.mentor_advice;
            advPanel.classList.remove('hidden');
        }

        // Render timeline roadmap
        renderTimeline(data.study_plan);

        // Progress
        const progressCard = document.getElementById('progress-card');
        if (progressCard) progressCard.classList.remove('hidden');
        restoreProgress();
        updateProgress();
    }

    // ─────────────────────────────────────────────
    // TIMELINE RENDERER (with week grouping)
    // ─────────────────────────────────────────────

    function renderTimeline(studyPlan) {
        const container = document.getElementById('roadmap-timeline');
        if (!container) return;

        let html = '';
        let currentWeek = 0;

        for (const day of studyPlan) {
            const weekNum = Math.ceil(day.day / 7);
            if (weekNum !== currentWeek) {
                if (currentWeek !== 0) html += '</div>'; // close prev group
                currentWeek = weekNum;
                html += `<div class="week-group">`;
                html += `<div class="week-label">Week ${weekNum}</div>`;
            }

            html += `<div class="timeline-day">`;
            html += `<div class="day-label">Day ${day.day}</div>`;
            day.tasks.forEach((task, idx) => {
                const taskId = `day-${day.day}-task-${idx}`;
                html += `<label class="task-item">`;
                html += `<input type="checkbox" data-task-id="${taskId}">`;
                html += `<span>${task}</span>`;
                html += `</label>`;
            });
            html += '</div>';
        }
        if (currentWeek !== 0) html += '</div>'; // close last group

        container.innerHTML = html;

        // Attach checkbox listeners
        container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', () => {
                saveProgress();
                updateProgress();
            });
        });
    }

    // ─────────────────────────────────────────────
    // PROGRESS — localStorage helpers
    // ─────────────────────────────────────────────

    function saveProgress() {
        const cbs = document.querySelectorAll('#roadmap-timeline input[type="checkbox"]');
        const state = {};
        cbs.forEach(cb => { state[cb.dataset.taskId] = cb.checked; });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }

    function restoreProgress() {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        try {
            const state = JSON.parse(raw);
            document.querySelectorAll('#roadmap-timeline input[type="checkbox"]').forEach(cb => {
                if (state[cb.dataset.taskId] === true) cb.checked = true;
            });
        } catch (e) {
            console.warn('Could not restore progress:', e);
        }
    }

    function updateProgress() {
        const cbs = document.querySelectorAll('#roadmap-timeline input[type="checkbox"]');
        const total = cbs.length;
        let done = 0;
        cbs.forEach(cb => { if (cb.checked) done++; });

        const pct = total > 0 ? Math.round((done / total) * 100) : 0;

        const fill = document.getElementById('progress-fill');
        const pctEl = document.getElementById('progress-pct');
        const label = document.getElementById('progress-label');

        if (fill) fill.style.width = pct + '%';
        if (pctEl) pctEl.textContent = pct + '%';
        if (label) label.textContent = `${done} of ${total} tasks complete`;
    }

    // ─────────────────────────────────────────────
    // AUTO-RESTORE on page load
    // ─────────────────────────────────────────────

    const savedRoadmap = localStorage.getItem(ROADMAP_KEY);
    if (savedRoadmap) {
        try {
            const data = JSON.parse(savedRoadmap);
            const meta = JSON.parse(localStorage.getItem(META_KEY) || '{}');
            switchToDashboard(data, meta.exam_name || '');
        } catch (e) {
            console.warn('Could not restore saved roadmap:', e);
        }
    }
});
