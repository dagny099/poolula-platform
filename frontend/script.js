// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalDocuments, documentTableBody, newChatButton;
let notificationBanner, notificationFiles, processNowButton, dismissBanner;
let uploadArea, fileInput, uploadProgress, uploadFileList;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalDocuments = document.getElementById('totalDocuments');
    documentTableBody = document.getElementById('documentTableBody');
    newChatButton = document.getElementById('newChatButton');
    
    // Document management elements
    notificationBanner = document.getElementById('notificationBanner');
    notificationFiles = document.getElementById('notificationFiles');
    processNowButton = document.getElementById('processNowButton');
    dismissBanner = document.getElementById('dismissBanner');
    uploadArea = document.getElementById('uploadArea');
    fileInput = document.getElementById('fileInput');
    uploadProgress = document.getElementById('uploadProgress');
    uploadFileList = document.getElementById('uploadFileList');
    
    setupEventListeners();
    createNewSession();
    checkForIncomingFiles();
    loadDocumentStats();
    updateCurrentDate();
    loadResources();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // New chat functionality
    newChatButton.addEventListener('click', startNewChat);
    
    // Document management functionality
    if (processNowButton) {
        processNowButton.addEventListener('click', processIncomingFiles);
    }
    if (dismissBanner) {
        dismissBanner.addEventListener('click', hideNotificationBanner);
    }
    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
    }
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        console.log('Making API request to:', `${API_URL}/query`);
        console.log('Request body:', {query: query, session_id: currentSessionId});
        
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });
        
        console.log('Response received:', response);

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        console.error('API Error:', error);
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
        
        // Also log to console for debugging
        console.error('Full error details:', error);
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Format sources with links
        const formattedSources = sources.map(source => {
            // Handle both old string format and new object format for backward compatibility
            if (typeof source === 'string') {
                return source;
            } else if (source.link) {
                // Create clickable link with descriptive text
                const linkText = source.lesson_number !== null 
                    ? `📹 Watch Lesson ${source.lesson_number}`
                    : `🎓 View Course Page`;
                return `<a href="${source.link}" target="_blank" rel="noopener noreferrer" class="source-link">${linkText}</a> (${source.text})`;
            } else {
                return source.text || source;
            }
        }).join(', ');
        
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${formattedSources}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('👋 Hello! I\'m your Poolula LLC Bookkeeping Assistant. I\'m here to help you manage your LLC compliance, understand tax obligations, and organize your business documentation.\n\n💼 **Get started easily** - Check out the sample questions in the sidebar, or ask me anything about your LLC\'s financial records, tax deadlines, or business requirements!', 'assistant', null, true);
}

function startNewChat() {
    // Clear current conversation
    currentSessionId = null;
    chatMessages.innerHTML = '';
    
    // Reset input field
    chatInput.value = '';
    chatInput.disabled = false;
    sendButton.disabled = false;
    
    // Add welcome message
    addMessage('👋 Hello! I\'m your Poolula LLC Bookkeeping Assistant. I\'m here to help you manage your LLC compliance, understand tax obligations, and organize your business documentation.\n\n💼 **Get started easily** - Check out the sample questions in the sidebar, or ask me anything about your LLC\'s financial records, tax deadlines, or business requirements!', 'assistant', null, true);
    
    // Focus on input for immediate use
    chatInput.focus();
    
    console.log('New chat session started');
}

// Load course statistics
async function loadDocumentStats() {
    try {
        console.log('Loading document stats...');
        const response = await fetch(`${API_URL}/documents`);
        if (!response.ok) throw new Error('Failed to load document stats');
        
        const data = await response.json();
        console.log('Document data received:', data);
        
        // Update stats in UI
        if (totalDocuments) {
            totalDocuments.textContent = data.total_documents;
        }
        
        // Update document table
        if (documentTableBody) {
            if (data.document_titles && data.document_titles.length > 0) {
                // Create array of document objects for sorting
                const documentData = data.document_titles.map(title => ({
                    title,
                    docType: getDocumentType(title),
                    tabNumber: getLLCBinderTab(title),
                    fileUrl: `${API_URL}/documents/${encodeURIComponent(title)}`
                }));
                
                // Sort by Tab first, then by Document type
                documentData.sort((a, b) => {
                    // Extract tab number for proper numeric sorting
                    const tabA = parseInt(a.tabNumber.replace('Tab ', ''));
                    const tabB = parseInt(b.tabNumber.replace('Tab ', ''));
                    
                    if (tabA !== tabB) {
                        return tabA - tabB; // Sort by tab number
                    }
                    return a.docType.localeCompare(b.docType); // Then by document type
                });
                
                documentTableBody.innerHTML = documentData
                    .map(doc => `
                        <tr>
                            <td class="document-type">${doc.docType}</td>
                            <td class="document-filename">
                                <a href="${doc.fileUrl}" target="_blank" rel="noopener noreferrer" class="document-link">
                                    ${doc.title}
                                </a>
                            </td>
                            <td class="document-tab">${doc.tabNumber}</td>
                        </tr>
                    `)
                    .join('');
            } else {
                documentTableBody.innerHTML = '<tr><td colspan="3" class="loading-cell"><span class="no-documents">No documents available</span></td></tr>';
            }
        }
        
    } catch (error) {
        console.error('Error loading document stats:', error);
        // Set default values on error
        if (totalDocuments) {
            totalDocuments.textContent = '0';
        }
        if (documentTableBody) {
            documentTableBody.innerHTML = '<tr><td colspan="3" class="loading-cell"><span class="error">Failed to load documents</span></td></tr>';
        }
    }
}

// Helper function to determine document type from filename
function getDocumentType(filename) {
    const lowerName = filename.toLowerCase();
    
    if (lowerName.includes('operating_agreement') || lowerName.includes('operating agreement')) {
        return '📋 Operating Agreement';
    } else if (lowerName.includes('articles')) {
        return '📜 Articles of Organization';
    } else if (lowerName.includes('ein')) {
        return '🆔 EIN Documentation';
    } else if (lowerName.includes('soa') || lowerName.includes('statement of authority')) {
        return '✅ Statement of Authority';
    } else if (lowerName.includes('letter')) {
        return '📧 Official Letter';
    } else if (lowerName.includes('accounting') || lowerName.includes('notes')) {
        return '📊 Accounting Records';
    } else if (lowerName.includes('.pdf')) {
        return '📄 PDF Document';
    } else if (lowerName.includes('.docx') || lowerName.includes('.doc')) {
        return '📝 Word Document';
    } else {
        return '📄 Document';
    }
}

// Helper function to determine LLC binder tab from filename
function getLLCBinderTab(filename) {
    const lowerName = filename.toLowerCase();
    
    // Tab 1 – Formation Documents
    if (lowerName.includes('articles') || lowerName.includes('operating_agreement') || 
        lowerName.includes('operating agreement') || lowerName.includes('llc_letter')) {
        return 'Tab 1';
    }
    
    // Tab 2 – Trust Authority Documents  
    if (lowerName.includes('soa') || lowerName.includes('statement of authority') || 
        lowerName.includes('trust') || lowerName.includes('authority')) {
        return 'Tab 2';
    }
    
    // Tab 3 – Property Ownership (no specific documents identified yet)
    if (lowerName.includes('deed') || lowerName.includes('title') || 
        lowerName.includes('closing') || lowerName.includes('hud')) {
        return 'Tab 3';
    }
    
    // Tab 4 – Insurance (no specific documents identified yet)
    if (lowerName.includes('insurance') || lowerName.includes('travelers') || 
        lowerName.includes('policy')) {
        return 'Tab 4';
    }
    
    // Tab 5 – Banking & Finance (no specific documents identified yet)
    if (lowerName.includes('banking') || lowerName.includes('nuvista') || 
        lowerName.includes('chase') || lowerName.includes('account')) {
        return 'Tab 5';
    }
    
    // Tab 6 – Accounting & Tax
    if (lowerName.includes('accounting') || lowerName.includes('notes') || 
        lowerName.includes('tax') || lowerName.includes('quickbooks')) {
        return 'Tab 6';
    }
    
    // Tab 7 – Meeting Minutes / Written Consents
    if (lowerName.includes('minutes') || lowerName.includes('consent') || 
        lowerName.includes('meeting') || lowerName.includes('annual')) {
        return 'Tab 7';
    }
    
    // Tab 8 – Contracts & Vendor Agreements
    if (lowerName.includes('contract') || lowerName.includes('lease') || 
        lowerName.includes('vendor') || lowerName.includes('agreement')) {
        return 'Tab 8';
    }
    
    // Tab 9 – Compliance Filings
    if (lowerName.includes('compliance') || lowerName.includes('filing') || 
        lowerName.includes('periodic') || lowerName.includes('sos')) {
        return 'Tab 9';
    }
    
    // Tab 10 – Miscellaneous / Correspondence
    if (lowerName.includes('correspondence') || lowerName.includes('letter') || 
        lowerName.includes('irs') || lowerName.includes('misc')) {
        return 'Tab 10';
    }
    
    // Default to Tab 10 for unclassified documents
    return 'Tab 10';
}


// Document Management Functions

// Check for incoming files on page load
async function checkForIncomingFiles() {
    try {
        const response = await fetch(`${API_URL}/incoming-files`);
        if (!response.ok) throw new Error('Failed to check incoming files');
        
        const data = await response.json();
        
        if (data.count > 0) {
            showNotificationBanner(data.files);
        }
    } catch (error) {
        console.error('Error checking incoming files:', error);
    }
}

// Show notification banner with file list
function showNotificationBanner(files) {
    if (!notificationBanner) return;
    
    const filesList = files.length > 3 
        ? `${files.slice(0, 3).join(', ')} and ${files.length - 3} more`
        : files.join(', ');
    
    notificationFiles.textContent = `Found ${files.length} file${files.length === 1 ? '' : 's'}: ${filesList}`;
    notificationBanner.style.display = 'block';
}

// Hide notification banner
function hideNotificationBanner() {
    if (notificationBanner) {
        notificationBanner.style.display = 'none';
    }
}

// Process incoming files
async function processIncomingFiles() {
    if (!processNowButton) return;
    
    try {
        // Disable button and show progress
        processNowButton.disabled = true;
        processNowButton.textContent = 'Processing...';
        
        const progressContainer = document.getElementById('processingProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        if (progressContainer) {
            progressContainer.style.display = 'block';
            progressFill.style.width = '10%';
            progressText.textContent = 'Starting processing...';
        }
        
        // Call processing API
        const response = await fetch(`${API_URL}/process-incoming`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to process files');
        
        const data = await response.json();
        
        // Update progress
        if (progressContainer) {
            progressFill.style.width = '100%';
            progressText.textContent = data.message;
        }
        
        // Wait a moment to show completion
        setTimeout(() => {
            hideNotificationBanner();
            loadDocumentStats(); // Refresh document list
            
            // Show success message
            if (data.processed_files.length > 0) {
                showTemporaryMessage(`Successfully processed ${data.processed_files.length} document${data.processed_files.length === 1 ? '' : 's'}!`);
            }
        }, 1000);
        
    } catch (error) {
        console.error('Error processing files:', error);
        showTemporaryMessage('Error processing files. Please try again.', 'error');
        
        // Reset button
        processNowButton.disabled = false;
        processNowButton.textContent = 'Process Now';
        
        const progressContainer = document.getElementById('processingProgress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }
}

// File upload drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    uploadFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    uploadFiles(files);
}

// Upload files to incoming folder
async function uploadFiles(files) {
    if (!files.length) return;
    
    // Show upload progress
    uploadProgress.style.display = 'block';
    uploadFileList.innerHTML = '';
    
    const results = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileItem = createFileUploadItem(file.name);
        uploadFileList.appendChild(fileItem);
        
        try {
            const result = await uploadSingleFile(file, fileItem);
            results.push(result);
        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
            updateFileUploadStatus(fileItem, 'error');
        }
    }
    
    // Check for newly uploaded files
    setTimeout(() => {
        checkForIncomingFiles();
        fileInput.value = ''; // Reset file input
        
        // Hide upload progress after a delay
        setTimeout(() => {
            uploadProgress.style.display = 'none';
        }, 2000);
    }, 500);
}

// Upload a single file
async function uploadSingleFile(file, fileItem) {
    updateFileUploadStatus(fileItem, 'uploading');
    
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
    }
    
    const data = await response.json();
    updateFileUploadStatus(fileItem, 'success');
    return data;
}

// Create file upload item UI
function createFileUploadItem(filename) {
    const item = document.createElement('div');
    item.className = 'upload-file-item';
    
    item.innerHTML = `
        <div class="upload-file-name">${filename}</div>
        <div class="upload-file-status uploading">Uploading...</div>
    `;
    
    return item;
}

// Update file upload status
function updateFileUploadStatus(fileItem, status) {
    const statusEl = fileItem.querySelector('.upload-file-status');
    if (!statusEl) return;
    
    statusEl.className = `upload-file-status ${status}`;
    
    switch (status) {
        case 'uploading':
            statusEl.textContent = 'Uploading...';
            break;
        case 'success':
            statusEl.textContent = 'Uploaded';
            break;
        case 'error':
            statusEl.textContent = 'Failed';
            break;
    }
}

// Show temporary message
function showTemporaryMessage(message, type = 'success') {
    const messageEl = document.createElement('div');
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#dc2626' : '#4A7C59'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        font-weight: 500;
        animation: slideIn 0.3s ease-out;
    `;
    messageEl.textContent = message;
    
    document.body.appendChild(messageEl);
    
    setTimeout(() => {
        messageEl.remove();
    }, 3000);
}

// Update current date display
function updateCurrentDate() {
    const currentDateEl = document.getElementById('currentDate');
    if (!currentDateEl) return;
    
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    
    currentDateEl.textContent = now.toLocaleDateString('en-US', options);
}

// Load resources from markdown file
async function loadResources() {
    const resourcesContent = document.getElementById('resourcesContent');
    if (!resourcesContent) return;
    
    try {
        const response = await fetch('/resources.md');
        if (!response.ok) throw new Error('Failed to load resources');
        
        const markdownText = await response.text();
        
        // Convert markdown to HTML using marked.js
        const htmlContent = marked.parse(markdownText);
        
        resourcesContent.innerHTML = htmlContent;
        
        // Add click handlers to external links
        const links = resourcesContent.querySelectorAll('a[href^="http"]');
        links.forEach(link => {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.classList.add('resource-link');
        });
        
    } catch (error) {
        console.error('Error loading resources:', error);
        resourcesContent.innerHTML = '<div class="error">Failed to load resources</div>';
    }
}