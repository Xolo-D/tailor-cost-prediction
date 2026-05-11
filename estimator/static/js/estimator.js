/* Tailor Cost Estimator – frontend JS
   Handles AJAX estimation + chat natural language input
*/

const CSRF = document.querySelector('meta[name="csrf-token"]')?.content || '';

// ── FORM LOADING STATE ───────────────────────────────────────────────────────
const form    = document.getElementById('estimateForm');
const estBtn  = document.getElementById('estBtn');
const btnTxt  = document.getElementById('btnTxt');
const btnDots = document.getElementById('btnDots');

if (form) {
    form.addEventListener('submit', () => {
        btnTxt.style.display  = 'none';
        btnDots.style.display = 'flex';
        estBtn.disabled = true;
    });
}

// ── RESET FORM ───────────────────────────────────────────────────────────────
function resetForm() {
    if (form) form.reset();
    const result = document.getElementById('result');
    if (result) result.classList.remove('vis');
}

// ── CHAT / NATURAL LANGUAGE INPUT ───────────────────────────────────────────
async function sendChat() {
    const input   = document.getElementById('chatIn');
    const message = input.value.trim();
    if (!message) return;

    input.disabled = true;

    try {
        const res  = await fetch('/api/chat/', {
            method:  'POST',
            headers: {
                'Content-Type':  'application/json',
                'X-CSRFToken':   CSRF,
            },
            body: JSON.stringify({ message }),
        });

        const data = await res.json();

        if (data.success) {
            renderResult(data);
            input.value = '';
        } else {
            showChatReply(data.reply || 'Could not parse that. Try: "silk dress 3m"');
        }
    } catch (err) {
        showChatReply('Network error. Please try again.');
    } finally {
        input.disabled = false;
        input.focus();
    }
}

function showChatReply(text) {
    const hint = document.querySelector('.hint');
    if (hint) {
        const orig = hint.innerHTML;
        hint.style.color = 'var(--amber)';
        hint.textContent  = text;
        setTimeout(() => { hint.innerHTML = orig; hint.style.color = ''; }, 4000);
    }
}

// ── RENDER RESULT FROM AJAX ──────────────────────────────────────────────────
function renderResult(data) {
    const result = document.getElementById('result');
    if (!result) return;

    // Cost panel
    document.getElementById('priceVal').textContent   = `R ${fmt(data.total_cost)}`;
    document.getElementById('priceRange').innerHTML   =
        `<strong>Overhead:</strong> R ${fmt(data.overhead_cost)}`;

    document.getElementById('costBreakItems').innerHTML = `
        <div class="break-row"><span class="break-key">Material</span><span class="break-val">R ${fmt(data.material_cost)}</span></div>
        <div class="break-row"><span class="break-key">Overhead (8%)</span><span class="break-val">R ${fmt(data.overhead_cost)}</span></div>
    `;

    // Material panel
    document.getElementById('matVal').textContent  = `R ${fmt(data.material_cost)}`;
    document.getElementById('matSub').innerHTML    =
        `<strong>${data.fabric_m}m</strong> × R${data.price_per_m}/m · ${data.fabric_type}`;

    document.getElementById('matBreakItems').innerHTML = `
        <div class="break-row"><span class="break-key">Fabric</span><span class="break-val mat-val-sm">${data.fabric_type}</span></div>
        <div class="break-row"><span class="break-key">Metres</span><span class="break-val mat-val-sm">${data.fabric_m}m</span></div>
        <div class="break-row"><span class="break-key">Price/m</span><span class="break-val mat-val-sm">R ${data.price_per_m}</span></div>
    `;

    // Breakdown strips
    const bd = document.getElementById('breakdown');
    if (bd) bd.innerHTML = `
        <div class="bk-cell"><div class="bk-key">Garment</div><div class="bk-val">${data.garment}</div></div>
        <div class="bk-cell"><div class="bk-key">Fabric</div><div class="bk-val">${data.fabric_type}</div></div>
        <div class="bk-cell"><div class="bk-key">Metres</div><div class="bk-val">${data.fabric_m}m</div></div>
        <div class="bk-cell"><div class="bk-key">Price/m</div><div class="bk-val">R${data.price_per_m}</div></div>
    `;

    const mb = document.getElementById('matBreakdown');
    if (mb) mb.innerHTML = `
        <div class="mat-cell"><div class="mat-key">Material Cost</div><div class="mat-val">R ${fmt(data.material_cost)}</div></div>
        <div class="mat-cell"><div class="bk-key">Total Cost</div><div class="bk-val" style="color:var(--amber);font-weight:700">R ${fmt(data.total_cost)}</div></div>
    `;

    result.classList.add('vis');
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function fmt(n) {
    return Number(n).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
