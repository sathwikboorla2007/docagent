// ==========================================================================
// DocuAgent — Frontend Client Logic
// ==========================================================================

// --- Application State ---
const state = {
    token: localStorage.getItem('session_token'),
    user: null,
    currentView: 'chat',
    documents: [],
    submissions: [],
    reminders: [],
    auditLogs: [],
    isLoginMode: true,
    activeDomain: null
};

// --- DOM Cache ---
const elements = {
    appContainer: document.getElementById('app-container'),
    authModal: document.getElementById('auth-modal'),
    uploadModal: document.getElementById('upload-modal'),
    newAppModal: document.getElementById('new-app-modal'),
    docSecurityModal: document.getElementById('doc-security-modal'),
    
    // Auth
    authForm: document.getElementById('auth-form'),
    authTitle: document.getElementById('auth-title'),
    authSubtitle: document.getElementById('auth-subtitle'),
    authName: document.getElementById('auth-name'),
    authEmail: document.getElementById('auth-email'),
    authPassword: document.getElementById('auth-password'),
    toggleAuthModeBtn: document.getElementById('toggle-auth-mode'),
    authSubmitBtn: document.getElementById('auth-submit-btn'),
    fillDemoBtn: document.getElementById('fill-demo-btn'),
    registerOnlyFields: document.querySelectorAll('.register-only'),
    
    // Header
    userInfo: document.getElementById('user-info'),
    userRole: document.getElementById('user-role'),
    userAvatar: document.getElementById('user-avatar'),
    logoutBtn: document.getElementById('logout-btn'),
    headerDomainText: document.getElementById('header-domain-text'),
    
    // Nav Badges
    vaultCount: document.getElementById('vault-count'),
    submissionsCount: document.getElementById('submissions-count'),
    remindersCount: document.getElementById('reminders-count'),
    navBtns: document.querySelectorAll('.nav-btn'),
    views: document.querySelectorAll('.view'),
    
    // Chat
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    chatMessages: document.getElementById('chat-messages'),
    starterCards: document.querySelectorAll('.starter-card'),
    
    // Documents (Vault)
    documentsGrid: document.getElementById('documents-grid'),
    documentsEmpty: document.getElementById('documents-empty'),
    uploadDocBtn: document.getElementById('upload-doc-btn'),
    docSearchInput: document.getElementById('doc-search-input'),
    docDomainFilter: document.getElementById('doc-domain-filter'),
    
    // Upload Form
    uploadForm: document.getElementById('upload-form'),
    uploadFile: document.getElementById('upload-file'),
    uploadDocType: document.getElementById('upload-doc-type'),
    uploadExpiry: document.getElementById('upload-expiry'),
    uploadDropzone: document.getElementById('upload-dropzone'),
    selectedFileName: document.getElementById('selected-file-name'),
    uploadCancelBtn: document.getElementById('upload-cancel-btn'),
    
    // Submissions
    submissionsList: document.getElementById('submissions-list'),
    submissionsEmpty: document.getElementById('submissions-empty'),
    createAppBtn: document.getElementById('create-app-btn'),
    startSubmissionBtn: document.getElementById('start-submission-btn'),
    newAppForm: document.getElementById('new-app-form'),
    
    // Reminders
    remindersGrid: document.getElementById('reminders-grid'),
    remindersEmpty: document.getElementById('reminders-empty'),
    scanRemindersBtn: document.getElementById('scan-reminders-btn'),
    
    // Audit Log
    auditTableBody: document.getElementById('audit-table-body'),
    auditTotalCount: document.getElementById('audit-total-count'),
    refreshAuditBtn: document.getElementById('refresh-audit-btn'),
    auditActionFilter: document.getElementById('audit-action-filter'),
    auditActorFilter: document.getElementById('audit-actor-filter'),
    
    // Toasts
    notificationsContainer: document.getElementById('notifications-container')
};

// --- Initialization ---
function init() {
    setupEventListeners();
    
    if (state.token) {
        fetchUserInfo();
    } else {
        showAuthModal();
    }
    
    // Background polling for audit logs & reminders
    setInterval(() => {
        if (state.token && state.currentView === 'audit') {
            fetchAuditLogs();
        }
    }, 15000);
}

// --- API Client ---
async function apiCall(endpoint, options = {}) {
    const headers = { 'Accept': 'application/json' };
    
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }
    
    try {
        const response = await fetch(endpoint, {
            ...options,
            headers: { ...headers, ...options.headers }
        });
        
        if (response.status === 401) {
            handleLogout();
            throw new Error('Session expired. Please log in again.');
        }
        
        const data = await response.json().catch(() => null);
        
        if (!response.ok) {
            const detail = (data && data.detail) || `API Error (${response.status})`;
            throw new Error(detail);
        }
        
        return data;
    } catch (error) {
        console.error(`API [${endpoint}] Error:`, error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// --- Authentication Flow ---
function showAuthModal() {
    elements.appContainer.classList.add('hidden');
    elements.authModal.classList.remove('hidden');
}

function hideAuthModal() {
    elements.authModal.classList.add('hidden');
    elements.appContainer.classList.remove('hidden');
}

function toggleAuthMode(e) {
    if (e) e.preventDefault();
    state.isLoginMode = !state.isLoginMode;
    
    elements.authTitle.textContent = state.isLoginMode ? 'Welcome to DocuAgent' : 'Create Zero-Knowledge Vault';
    elements.authSubtitle.textContent = state.isLoginMode ? 'Secure access to your personal document vault & agent' : 'Client-side encrypted with AES-GCM and automated PII masking';
    elements.authSubmitBtn.textContent = state.isLoginMode ? 'Sign In' : 'Register Vault';
    elements.toggleAuthModeBtn.textContent = state.isLoginMode ? 'Need an account? Register with Zero-Knowledge Vault' : 'Already registered? Sign In';
    
    elements.registerOnlyFields.forEach(el => {
        if (state.isLoginMode) el.classList.add('hidden');
        else el.classList.remove('hidden');
    });
}

function fillDemoCredentials() {
    elements.authEmail.value = 'demo@example.com';
    elements.authPassword.value = 'demo123';
    if (!state.isLoginMode) {
        toggleAuthMode();
    }
    showNotification('Filled demo credentials! Click Sign In to continue.', 'info');
}

async function handleAuth(e) {
    e.preventDefault();
    const email = elements.authEmail.value.trim();
    const password = elements.authPassword.value;
    
    try {
        let data;
        if (state.isLoginMode) {
            data = await apiCall('/api/users/login', {
                method: 'POST',
                body: { email, password }
            });
        } else {
            const name = elements.authName.value.trim() || 'Demo User';
            data = await apiCall('/api/users/register', {
                method: 'POST',
                body: { name, email, password }
            });
        }
        
        state.token = data.session_token;
        localStorage.setItem('session_token', state.token);
        elements.authPassword.value = '';
        
        await fetchUserInfo();
        showNotification('Authenticated securely. Welcome to DocuAgent!', 'success');
    } catch (error) {
        // Handled in apiCall
    }
}

async function fetchUserInfo() {
    try {
        const data = await apiCall('/api/users/me');
        state.user = data;
        
        elements.userInfo.textContent = data.email_masked || 'user@example.com';
        elements.userRole.textContent = `${data.role} — ${data.name}`;
        elements.userAvatar.textContent = (data.name || 'U').charAt(0).toUpperCase();
        
        hideAuthModal();
        
        // Fetch all initial views data
        await Promise.all([
            fetchDocuments(),
            fetchSubmissions(),
            fetchReminders(),
            fetchAuditLogs()
        ]);
    } catch (error) {
        showAuthModal();
    }
}

function handleLogout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('session_token');
    showAuthModal();
}

// --- Navigation & View Switching ---
function switchView(viewId) {
    state.currentView = viewId;
    
    elements.navBtns.forEach(btn => {
        if (btn.dataset.view === viewId) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    
    elements.views.forEach(view => {
        if (view.id === `view-${viewId}`) {
            view.classList.remove('hidden');
            setTimeout(() => view.classList.add('active'), 10);
        } else {
            view.classList.remove('active');
            setTimeout(() => view.classList.add('hidden'), 250);
        }
    });
    
    if (viewId === 'documents') fetchDocuments();
    if (viewId === 'submissions') fetchSubmissions();
    if (viewId === 'reminders') fetchReminders();
    if (viewId === 'audit') fetchAuditLogs();
}

// --- 1. Chat & Agentic Bureaucracy Copilot ---
async function handleChatSubmit(e) {
    if (e) e.preventDefault();
    const message = elements.chatInput.value.trim();
    if (!message) return;
    
    addChatMessage(message, 'user');
    elements.chatInput.value = '';
    
    // Show typing indicator
    const typingId = showTypingIndicator();
    
    try {
        const data = await apiCall('/api/chat', {
            method: 'POST',
            body: { message }
        });
        
        removeTypingIndicator(typingId);
        
        // Save active domain in state if returned
        if (data.domain) {
            state.activeDomain = data.domain;
            updateHeaderDomainText(data.domain);
        }
        
        // Render rich agent response
        addChatMessage(data.response, 'agent', data);
        
        // Refresh documents, submissions, reminders if actions taken
        if (data.actions_taken && data.actions_taken.length > 0) {
            fetchDocuments();
            fetchSubmissions();
            fetchReminders();
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        addChatMessage('⚠️ Sorry, I encountered an issue connecting to the orchestrator agent. Please try again.', 'agent');
    }
}

function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'message agent-message';
    div.innerHTML = `
        <div class="msg-avatar agent-avatar">🛡️</div>
        <div class="message-bubble" style="padding: 12px 18px;">
            <span style="display:inline-flex; gap: 4px; align-items: center; color: var(--text-muted); font-size: 13px;">
                <span class="typing-dot" style="animation: pulse 1s infinite 0.1s;">●</span>
                <span class="typing-dot" style="animation: pulse 1s infinite 0.2s;">●</span>
                <span class="typing-dot" style="animation: pulse 1s infinite 0.3s;">●</span>
                <span style="margin-left: 6px;">Analyzing requirements & checking vault...</span>
            </span>
        </div>
    `;
    elements.chatMessages.appendChild(div);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function addChatMessage(text, sender, meta = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;
    
    const avatar = sender === 'user' 
        ? `<div class="msg-avatar user-avatar-msg">👤</div>`
        : `<div class="msg-avatar agent-avatar">🛡️</div>`;
    
    // Format message text: bold markdown, bullet lists, code
    let formattedText = formatMarkdownText(text);
    
    let bubbleHtml = `<div class="message-bubble"><div class="message-text">${formattedText}</div>`;
    
    // ── Rich Interactive Gap Analysis Card ──
    if (meta && meta.requirements) {
        const req = meta.requirements;
        const total = req.total_required || 0;
        const metList = req.documents_met || [];
        const missingList = req.documents_missing || [];
        const expiredList = req.documents_expired || [];
        const pct = req.completion_percentage !== undefined ? req.completion_percentage : 0;
        const isComplete = pct >= 100;
        
        bubbleHtml += `
            <div class="gap-analysis-card">
                <div class="gap-header">
                    <div class="gap-domain-title">
                        <span>📋</span>
                        <span>${req.display_name || formatDocType(req.domain)} Readiness</span>
                    </div>
                    <span class="badge ${isComplete ? 'badge-verified' : 'badge-pending'}">${pct}% Ready</span>
                </div>
                
                <div class="progress-container">
                    <div class="progress-label-bar">
                        <span>${metList.length} of ${total} Documents Ready</span>
                        <span>${pct}% Complete</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill ${isComplete ? 'complete' : ''}" style="width: ${pct}%;"></div>
                    </div>
                </div>

                <div class="gap-checklist">
        `;
        
        // Met documents (Reused from Vault!)
        metList.forEach(item => {
            const reusedFrom = item.reused_from ? ` <span class="reuse-tag">Vault: ${formatDocType(item.reused_from)}</span>` : ` <span class="reuse-tag">Reused</span>`;
            bubbleHtml += `
                <div class="checklist-item met">
                    <div class="checklist-item-left">
                        <span class="status-icon">✅</span>
                        <span>${item.description || formatDocType(item.doc_type)}</span>
                        ${reusedFrom}
                    </div>
                    <span class="badge badge-verified">Ready</span>
                </div>
            `;
        });
        
        // Expired documents
        expiredList.forEach(item => {
            bubbleHtml += `
                <div class="checklist-item expired">
                    <div class="checklist-item-left">
                        <span class="status-icon">⚠️</span>
                        <span>${item.description || formatDocType(item.doc_type)} (Expired)</span>
                    </div>
                    <button class="btn btn-xs btn-outline" onclick="openUploadModal('${item.doc_type}')">Re-upload</button>
                </div>
            `;
        });
        
        // Missing documents
        missingList.forEach(item => {
            bubbleHtml += `
                <div class="checklist-item missing">
                    <div class="checklist-item-left">
                        <span class="status-icon">❌</span>
                        <span>${item.description || formatDocType(item.doc_type)}</span>
                    </div>
                    <button class="btn btn-xs btn-primary" onclick="openUploadModal('${item.doc_type}')">+ Upload</button>
                </div>
            `;
        });
        
        bubbleHtml += `</div>`; // end gap-checklist
        
        // Submit button when 100%
        if (isComplete) {
            bubbleHtml += `
                <button class="btn btn-primary btn-submit-action" onclick="submitApplicationFromChat('${req.domain}')">
                    🚀 All Documents Ready — File Application Now
                </button>
            `;
        }
        
        bubbleHtml += `</div>`; // end gap-analysis-card
    }
    
    // ── Suggestions Chips ──
    if (meta && meta.suggestions && meta.suggestions.length > 0) {
        bubbleHtml += `<div class="suggestions-row">`;
        meta.suggestions.forEach(sug => {
            bubbleHtml += `<button type="button" class="chat-chip" onclick="handleChipClick('${escapeQuotes(sug)}')">${sug}</button>`;
        });
        bubbleHtml += `</div>`;
    }
    
    bubbleHtml += `</div>`; // end message-bubble
    
    msgDiv.innerHTML = avatar + bubbleHtml;
    elements.chatMessages.appendChild(msgDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function handleChipClick(text) {
    elements.chatInput.value = text;
    handleChatSubmit();
}

function submitApplicationFromChat(domain) {
    elements.chatInput.value = `Please submit my ${formatDocType(domain)} application now.`;
    handleChatSubmit();
}

function updateHeaderDomainText(domain) {
    if (!domain) return;
    elements.headerDomainText.textContent = `Active Domain: ${formatDocType(domain)}`;
}

// Simple Markdown Formatter
function formatMarkdownText(text) {
    if (!text) return '';
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
        
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italics
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Code snippets
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bullet points
    html = html.replace(/^[•\-\*]\s*(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    // Paragraphs
    html = html.split('\n\n').map(p => p.startsWith('<ul>') ? p : `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    
    return html;
}

// --- 2. Document Vault View ---
async function fetchDocuments() {
    try {
        const data = await apiCall('/api/documents');
        state.documents = data.documents || [];
        elements.vaultCount.textContent = state.documents.length;
        renderDocuments();
    } catch (error) {
        console.error('Failed to fetch documents:', error);
    }
}

function renderDocuments() {
    elements.documentsGrid.innerHTML = '';
    
    const searchTerm = elements.docSearchInput.value.toLowerCase().trim();
    const domainFilter = elements.docDomainFilter.value;
    
    const filteredDocs = state.documents.filter(doc => {
        const matchesSearch = !searchTerm || 
            doc.doc_type.toLowerCase().includes(searchTerm) || 
            (doc.original_filename && doc.original_filename.toLowerCase().includes(searchTerm));
            
        let matchesDomain = true;
        if (domainFilter) {
            matchesDomain = doc.linked_domains && doc.linked_domains.includes(domainFilter);
        }
        
        return matchesSearch && matchesDomain;
    });
    
    if (filteredDocs.length === 0) {
        elements.documentsEmpty.classList.remove('hidden');
        return;
    }
    
    elements.documentsEmpty.classList.add('hidden');
    
    filteredDocs.forEach(doc => {
        const card = document.createElement('div');
        const status = doc.status || 'pending';
        card.className = `doc-card ${status}`;
        
        // PII Masking extraction
        let piiHtml = '';
        if (doc.pii_fields_masked && Object.keys(doc.pii_fields_masked).length > 0) {
            const firstKey = Object.keys(doc.pii_fields_masked)[0];
            const maskedVal = doc.pii_fields_masked[firstKey];
            piiHtml = `<div class="pii-chip"><span class="pii-lock">🔒</span> ${formatDocType(firstKey)}: ${maskedVal}</div>`;
        }
        
        // Linked domains tags
        let domainsHtml = '';
        if (doc.linked_domains && Array.isArray(doc.linked_domains) && doc.linked_domains.length > 0) {
            domainsHtml = `<div class="linked-domains-row">`;
            doc.linked_domains.forEach(d => {
                const icon = d.includes('visa') ? '✈️' : d.includes('loan') ? '🏠' : '🏢';
                domainsHtml += `<span class="domain-tag">${icon} ${formatDocType(d)}</span>`;
            });
            domainsHtml += `</div>`;
        }
        
        // Expiry date warning
        let expiryHtml = '';
        if (doc.expires_at) {
            const expDate = new Date(doc.expires_at);
            const isExpired = expDate < new Date();
            expiryHtml = `<div style="color: ${isExpired ? 'var(--error)' : 'var(--text-muted)'}; font-weight: ${isExpired ? '700' : '500'};">Expires: ${formatDate(doc.expires_at, true)}</div>`;
        }
        
        card.innerHTML = `
            <div class="doc-header">
                <div class="doc-title-group">
                    <div class="doc-type-icon">${getDocTypeIcon(doc.doc_type)}</div>
                    <div>
                        <div class="doc-name">${formatDocType(doc.doc_type)}</div>
                        <div class="doc-filename" title="${doc.original_filename || ''}">${doc.original_filename || 'Secure Upload'}</div>
                    </div>
                </div>
                <span class="badge badge-${status}">${status}</span>
            </div>
            
            ${piiHtml}
            ${domainsHtml}
            
            <div class="doc-meta">
                <div>Uploaded: ${formatDate(doc.uploaded_at, true)}</div>
                ${expiryHtml}
            </div>
            
            <div class="doc-actions">
                <button class="btn btn-outline btn-sm" onclick="showDocSecurityModal('${doc.id}')">🛡️ Security Info</button>
                <button class="btn btn-danger btn-sm" onclick="deleteDocument('${doc.id}')">Delete</button>
            </div>
        `;
        
        elements.documentsGrid.appendChild(card);
    });
}

function getDocTypeIcon(type) {
    if (!type) return '📄';
    if (type.includes('passport')) return '🛂';
    if (type.includes('bank')) return '💳';
    if (type.includes('pan') || type.includes('aadhaar') || type.includes('id')) return '🪪';
    if (type.includes('salary') || type.includes('income')) return '💵';
    if (type.includes('insurance')) return '🏥';
    if (type.includes('flight') || type.includes('itinerary')) return '✈️';
    if (type.includes('hotel')) return '🏨';
    if (type.includes('property')) return '🏠';
    if (type.includes('business') || type.includes('registration')) return '🏢';
    if (type.includes('photo')) return '🖼️';
    return '📄';
}

function openUploadModal(prefillDocType = null) {
    elements.uploadModal.classList.remove('hidden');
    if (prefillDocType) {
        elements.uploadDocType.value = prefillDocType;
    }
}

function closeUploadModal() {
    elements.uploadModal.classList.add('hidden');
    elements.uploadForm.reset();
    elements.selectedFileName.textContent = '';
    elements.selectedFileName.classList.add('hidden');
}

async function handleUploadSubmit(e) {
    e.preventDefault();
    const file = elements.uploadFile.files[0];
    if (!file) {
        showNotification('Please select a document file to upload.', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', elements.uploadDocType.value);
    
    if (elements.uploadExpiry.value) {
        formData.append('expires_at', elements.uploadExpiry.value);
    }
    
    // Collect checked domains
    const checkedDomains = Array.from(document.querySelectorAll('input[name="linked_domain"]:checked'))
        .map(cb => cb.value);
    if (checkedDomains.length > 0) {
        formData.append('linked_domains_json', JSON.stringify(checkedDomains));
    }
    
    const submitBtn = document.getElementById('upload-submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Encrypting & Uploading...';
    
    try {
        await apiCall('/api/documents/upload', {
            method: 'POST',
            body: formData
        });
        
        closeUploadModal();
        showNotification(`Encrypted & stored: ${formatDocType(elements.uploadDocType.value)} in Vault!`, 'success');
        
        await fetchDocuments();
        await fetchReminders();
        
        // Notify chat
        if (state.currentView === 'chat') {
            addChatMessage(`I've securely encrypted and deposited your **${formatDocType(elements.uploadDocType.value)}** into the Vault. Cross-domain requirements have been updated!`, 'agent');
        }
    } catch (error) {
        // Handled in apiCall
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Encrypt & Upload';
    }
}

async function deleteDocument(id) {
    if (!confirm('Are you sure you want to permanently delete this encrypted document from your vault?')) return;
    
    try {
        await apiCall(`/api/documents/${id}`, { method: 'DELETE' });
        showNotification('Document deleted from vault.', 'info');
        await fetchDocuments();
        await fetchReminders();
    } catch (error) {
        // Handled in apiCall
    }
}

function showDocSecurityModal(docId) {
    const doc = state.documents.find(d => d.id === docId);
    if (!doc) return;
    
    const container = document.getElementById('doc-security-content');
    
    let piiSummary = 'No sensitive PII fields detected.';
    if (doc.pii_fields_masked && Object.keys(doc.pii_fields_masked).length > 0) {
        piiSummary = Object.entries(doc.pii_fields_masked)
            .map(([k, v]) => `• <strong>${formatDocType(k)}:</strong> <code>${v}</code>`)
            .join('<br>');
    }
    
    container.innerHTML = `
        <div class="sec-field-group">
            <div class="sec-field-label">Encryption Algorithm</div>
            <div class="sec-field-val">AES-GCM-256 (Authenticated Encryption with 128-bit Tag)</div>
        </div>
        <div class="sec-field-group">
            <div class="sec-field-label">Document ID & Storage Vault</div>
            <div class="sec-field-val">${doc.id}</div>
        </div>
        <div class="sec-field-group">
            <div class="sec-field-label">Zero-Knowledge PII Masking Status</div>
            <div style="font-size: 13px; color: var(--text-main); margin-top: 4px;">
                ${piiSummary}
            </div>
        </div>
        <div class="sec-field-group">
            <div class="sec-field-label">Cross-Domain Authorization</div>
            <div class="sec-field-val">${(doc.linked_domains || ['None']).join(', ')}</div>
        </div>
    `;
    
    elements.docSecurityModal.classList.remove('hidden');
}

function closeDocSecurityModal() {
    elements.docSecurityModal.classList.add('hidden');
}

// --- 3. Submissions Tracker View ---
async function fetchSubmissions() {
    try {
        const data = await apiCall('/api/submissions');
        state.submissions = data.submissions || [];
        elements.submissionsCount.textContent = state.submissions.length;
        renderSubmissions();
    } catch (error) {
        console.error('Failed to fetch submissions:', error);
    }
}

function renderSubmissions() {
    elements.submissionsList.innerHTML = '';
    
    if (state.submissions.length === 0) {
        elements.submissionsEmpty.classList.remove('hidden');
        return;
    }
    
    elements.submissionsEmpty.classList.add('hidden');
    
    const pipelineStages = ['draft', 'submitted', 'in_review', 'approved'];
    
    state.submissions.forEach(sub => {
        const card = document.createElement('div');
        card.className = 'sub-card';
        
        let currentIndex = pipelineStages.indexOf(sub.status);
        if (currentIndex === -1) currentIndex = 0;
        
        let trackHtml = `<div class="pipeline-track">`;
        pipelineStages.forEach((stage, idx) => {
            let stageClass = '';
            let iconText = idx + 1;
            
            if (idx < currentIndex) {
                stageClass = 'completed';
                iconText = '✓';
            } else if (idx === currentIndex) {
                stageClass = 'active';
            }
            
            trackHtml += `
                <div class="pipeline-step ${stageClass}">
                    <div class="step-num">${iconText}</div>
                    <div class="step-name">${formatDocType(stage)}</div>
                </div>
            `;
        });
        trackHtml += `</div>`;
        
        card.innerHTML = `
            <div class="sub-top">
                <div class="sub-domain-title">
                    <span>${sub.domain.includes('visa') ? '✈️' : sub.domain.includes('loan') ? '🏠' : '🏢'}</span>
                    <span>${formatDocType(sub.domain)} Application</span>
                </div>
                <span class="ref-badge">Ref: ${sub.external_ref_id || 'PENDING'}</span>
            </div>
            
            ${trackHtml}
            
            <div class="sub-bottom">
                <div class="sub-meta-notes">
                    <div>Last Updated: ${formatDate(sub.updated_at || sub.created_at)}</div>
                    <div>${sub.notes ? `Note: ${sub.notes}` : 'Automated workflow active'}</div>
                </div>
                <div>
                    <button class="btn btn-outline btn-sm" onclick="advanceSubmissionStatus('${sub.id}')">
                        ⟳ Check Live Status
                    </button>
                </div>
            </div>
        `;
        
        elements.submissionsList.appendChild(card);
    });
}

async function advanceSubmissionStatus(subId) {
    try {
        const result = await apiCall(`/api/submissions/${subId}/status`);
        showNotification(`Application status: ${result.status.toUpperCase()} (${result.external_ref_id})`, 'info');
        await fetchSubmissions();
    } catch (error) {
        // Handled in apiCall
    }
}

function openNewAppModal() {
    elements.newAppModal.classList.remove('hidden');
}

function closeNewAppModal() {
    elements.newAppModal.classList.add('hidden');
    elements.newAppForm.reset();
}

async function handleNewAppSubmit(e) {
    e.preventDefault();
    const domain = document.getElementById('app-domain').value;
    const notes = document.getElementById('app-notes').value.trim();
    
    try {
        await apiCall('/api/submissions/create', {
            method: 'POST',
            body: { domain, notes }
        });
        
        closeNewAppModal();
        showNotification(`Created draft application for ${formatDocType(domain)}!`, 'success');
        await fetchSubmissions();
    } catch (error) {
        // Handled
    }
}

// --- 4. Proactive Reminders View ---
async function fetchReminders() {
    try {
        const data = await apiCall('/api/reminders');
        state.reminders = data.reminders || [];
        
        const activeCount = state.reminders.filter(r => !r.is_sent).length;
        if (activeCount > 0) {
            elements.remindersCount.textContent = activeCount;
            elements.remindersCount.classList.remove('hidden');
        } else {
            elements.remindersCount.classList.add('hidden');
        }
        
        renderReminders();
    } catch (error) {
        console.error('Failed to fetch reminders:', error);
    }
}

function renderReminders() {
    elements.remindersGrid.innerHTML = '';
    
    if (state.reminders.length === 0) {
        elements.remindersEmpty.classList.remove('hidden');
        return;
    }
    
    elements.remindersEmpty.classList.add('hidden');
    
    state.reminders.forEach(r => {
        const card = document.createElement('div');
        const isUrgent = r.reminder_type === 'expiry' && r.message.toLowerCase().includes('urgent');
        const isWarning = r.reminder_type === 'expiry';
        const isResolved = r.is_sent;
        
        let urgencyClass = isResolved ? 'resolved' : isUrgent ? 'urgent' : isWarning ? 'warning' : '';
        card.className = `reminder-card ${urgencyClass}`;
        
        card.innerHTML = `
            <div>
                <div class="rem-top">
                    <span class="rem-type">⏰ ${formatDocType(r.reminder_type)}</span>
                    <span class="rem-due-badge ${isUrgent ? 'urgent' : ''}">${isResolved ? 'Resolved' : formatDate(r.due_date, true)}</span>
                </div>
                <div class="rem-message">${r.message}</div>
            </div>
            
            <div class="rem-bottom">
                <span style="font-size: 11px; color: var(--text-dim);">${r.domain ? `Domain: ${r.domain}` : 'General'}</span>
                ${!isResolved ? `<button class="btn btn-sm btn-outline" onclick="dismissReminder('${r.id}')">✓ Mark Done</button>` : `<span style="font-size: 11px; color: var(--success);">Completed</span>`}
            </div>
        `;
        
        elements.remindersGrid.appendChild(card);
    });
}

async function dismissReminder(id) {
    try {
        await apiCall(`/api/reminders/${id}/dismiss`, { method: 'POST' });
        showNotification('Reminder marked as completed', 'success');
        await fetchReminders();
    } catch (error) {
        // Handled
    }
}

async function triggerScanExpirations() {
    try {
        const res = await apiCall('/api/reminders/scan', { method: 'POST' });
        showNotification(res.message, 'success');
        await fetchReminders();
    } catch (error) {
        // Handled
    }
}

// --- 5. Security Audit Log View ---
async function fetchAuditLogs() {
    try {
        const actionFilter = elements.auditActionFilter.value;
        const actorFilter = elements.auditActorFilter.value;
        
        let url = '/api/audit/log?per_page=50';
        if (actionFilter) url += `&action=${actionFilter}`;
        
        const data = await apiCall(url);
        let entries = data.entries || [];
        
        if (actorFilter) {
            entries = entries.filter(e => e.actor === actorFilter);
        }
        
        state.auditLogs = entries;
        elements.auditTotalCount.textContent = `Displaying ${entries.length} immutable security entries (Total: ${data.total || entries.length})`;
        renderAuditLogs();
    } catch (error) {
        console.error('Failed to fetch audit log:', error);
    }
}

function renderAuditLogs() {
    elements.auditTableBody.innerHTML = '';
    
    state.auditLogs.forEach(entry => {
        const tr = document.createElement('tr');
        
        let resultColor = '#34d399';
        if (entry.result === 'denied') resultColor = '#fb7185';
        if (entry.result === 'error') resultColor = '#fbbf24';
        
        const actorClass = `actor-${entry.actor || 'system'}`;
        
        tr.innerHTML = `
            <td style="font-family: monospace; font-size: 12px; color: var(--text-dim);">${formatDate(entry.timestamp)}</td>
            <td><span class="actor-badge ${actorClass}">${entry.actor || 'system'}</span></td>
            <td><code style="color: #38bdf8; font-weight: 600;">${entry.action}</code></td>
            <td>${entry.resource_type || '-'}</td>
            <td style="color: ${resultColor}; font-weight: 700; text-transform: uppercase; font-size: 11px;">${entry.result}</td>
            <td style="max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeQuotes(entry.details || '')}">
                ${entry.details || '-'}
            </td>
        `;
        
        elements.auditTableBody.appendChild(tr);
    });
}

// --- Utilities ---
function formatDocType(type) {
    if (!type) return '';
    return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function formatDate(dateStr, dateOnly = false) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    if (dateOnly) {
        return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    }
    return d.toLocaleString(undefined, { 
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
}

function escapeQuotes(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function showNotification(message, type = 'info') {
    const notif = document.createElement('div');
    notif.className = `notification ${type}`;
    
    const icon = type === 'success' ? '✅' : type === 'error' ? '⚠️' : 'ℹ️';
    notif.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    
    elements.notificationsContainer.appendChild(notif);
    
    setTimeout(() => {
        notif.style.opacity = '0';
        notif.style.transform = 'translateX(100%)';
        setTimeout(() => notif.remove(), 300);
    }, 4500);
}

// --- Event Listeners Setup ---
function setupEventListeners() {
    // Auth
    elements.authForm.addEventListener('submit', handleAuth);
    elements.toggleAuthModeBtn.addEventListener('click', toggleAuthMode);
    elements.fillDemoBtn.addEventListener('click', fillDemoCredentials);
    elements.logoutBtn.addEventListener('click', handleLogout);
    
    // Nav View Switching
    elements.navBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const view = btn.dataset.view;
            if (view) switchView(view);
        });
    });
    
    // Chat
    elements.chatForm.addEventListener('submit', handleChatSubmit);
    
    // Starters
    elements.starterCards.forEach(card => {
        card.addEventListener('click', () => {
            const prompt = card.dataset.prompt;
            if (prompt) {
                elements.chatInput.value = prompt;
                handleChatSubmit();
            }
        });
    });
    
    // Documents
    elements.uploadDocBtn.addEventListener('click', () => openUploadModal());
    elements.uploadCancelBtn.addEventListener('click', closeUploadModal);
    elements.uploadForm.addEventListener('submit', handleUploadSubmit);
    
    elements.docSearchInput.addEventListener('input', renderDocuments);
    elements.docDomainFilter.addEventListener('change', renderDocuments);
    
    // Dropzone
    elements.uploadFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            elements.selectedFileName.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            elements.selectedFileName.classList.remove('hidden');
        }
    });
    
    elements.uploadDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadDropzone.classList.add('dragover');
    });
    elements.uploadDropzone.addEventListener('dragleave', () => {
        elements.uploadDropzone.classList.remove('dragover');
    });
    elements.uploadDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadDropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            elements.uploadFile.files = e.dataTransfer.files;
            const file = e.dataTransfer.files[0];
            elements.selectedFileName.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            elements.selectedFileName.classList.remove('hidden');
        }
    });
    
    // Submissions
    elements.createAppBtn.addEventListener('click', openNewAppModal);
    elements.startSubmissionBtn.addEventListener('click', openNewAppModal);
    elements.newAppForm.addEventListener('submit', handleNewAppSubmit);
    
    // Reminders
    elements.scanRemindersBtn.addEventListener('click', triggerScanExpirations);
    
    // Audit
    elements.refreshAuditBtn.addEventListener('click', fetchAuditLogs);
    elements.auditActionFilter.addEventListener('change', fetchAuditLogs);
    elements.auditActorFilter.addEventListener('change', fetchAuditLogs);
}

// Boot on DOM Ready
document.addEventListener('DOMContentLoaded', init);
