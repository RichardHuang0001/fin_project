// Initialize Lucide Icons
lucide.createIcons();

// State management
let conversations = JSON.parse(localStorage.getItem('fin_conversations') || '[]');
let currentChatId = null;
let isAnalyzing = false;
let currentAbortController = null;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const historyList = document.getElementById('history-list');
const chatContainer = document.getElementById('chat-container');
const welcomeScreen = document.getElementById('welcome-screen');
const userInput = document.getElementById('user-input');
const toast = document.getElementById('toast');

if (!welcomeScreen || !chatContainer) {
    console.error('Critical DOM elements not found!');
}
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const currentChatTitle = document.getElementById('current-chat-title');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');

// Constants
const API_URL = 'http://localhost:8000/api/analyze';

// Functions
function saveConversations() {
    localStorage.setItem('fin_conversations', JSON.stringify(conversations));
}

function updateHistoryUI() {
    historyList.innerHTML = '';
    conversations.forEach(chat => {
        const item = document.createElement('div');
        item.className = `mx-2 p-2.5 rounded-xl cursor-pointer transition-all flex items-center justify-between group ${chat.id === currentChatId ? 'sidebar-item-active' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`;
        item.innerHTML = `
            <div class="flex items-center gap-2.5 flex-1 min-w-0" onclick="loadChat('${chat.id}')">
                <i data-lucide="message-square" size="14" class="${chat.id === currentChatId ? 'text-blue-600' : 'text-slate-400'}"></i>
                <span class="truncate text-xs font-medium">${chat.title}</span>
            </div>
            <button class="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-opacity" onclick="deleteChat('${chat.id}', event)">
                <i data-lucide="x" size="12"></i>
            </button>
        `;
        historyList.appendChild(item);
    });
    lucide.createIcons();
}

function createNewChat() {
    const newChat = {
        id: Date.now().toString(),
        title: '新对话',
        messages: [],
        timestamp: new Date().toISOString()
    };
    conversations.unshift(newChat);
    currentChatId = newChat.id;
    saveConversations();
    loadChat(newChat.id);
    updateHistoryUI();
}

function loadChat(chatId) {
    currentChatId = chatId;
    const chat = conversations.find(c => c.id === chatId);
    if (!chat) return;

    currentChatTitle.innerText = chat.title;
    
    // Clear the container safely
    while (chatContainer.firstChild) {
        chatContainer.removeChild(chatContainer.firstChild);
    }
    
    if (chat.messages.length === 0) {
        chatContainer.appendChild(welcomeScreen);
    } else {
        chat.messages.forEach(msg => renderMessage(msg));
    }
    
    updateHistoryUI();
    scrollToBottom();
}

function deleteChat(chatId, event) {
    event.stopPropagation();
    conversations = conversations.filter(c => c.id !== chatId);
    if (currentChatId === chatId) {
        currentChatId = conversations.length > 0 ? conversations[0].id : null;
    }
    saveConversations();
    if (currentChatId) {
        loadChat(currentChatId);
    } else {
        location.reload();
    }
    updateHistoryUI();
}

function renderMessage(msg) {
    // Hide welcome screen if still present
    const welcome = document.getElementById('welcome-screen');
    if (welcome) {
        welcome.remove();
    }
    
    const wrapper = document.createElement('div');
    wrapper.className = `max-w-4xl mx-auto flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`;
    
    const avatar = document.createElement('div');
    avatar.className = `w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-1 ${msg.role === 'user' ? 'hidden' : 'bg-blue-50 text-blue-600 border border-blue-100'}`;
    avatar.innerHTML = '<i data-lucide="sparkles" size="16"></i>';
    
    const content = document.createElement('div');
    content.className = `flex flex-col gap-2 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`;
    
    const bubble = document.createElement('div');
    bubble.className = `p-4 text-sm leading-relaxed ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant w-full markdown-body'}`;
    
    if (msg.role === 'assistant') {
        // Only show original content, no fragments combining
        bubble.innerHTML = marked.parse(msg.content);
    } else {
        bubble.innerText = msg.content;
    }
    
    content.appendChild(bubble);
    
    if (msg.role === 'assistant') {
        const actions = document.createElement('div');
        actions.className = 'flex items-center gap-1 mt-1 px-2';
        const msgId = `msg-${Date.now()}`;
        actions.innerHTML = `
            <div class="relative inline-block">
                <button class="action-btn p-1 rounded-lg transition-colors" onclick="toggleDownloadDropdown('${msgId}')" title="下载">
                    <i data-lucide="download" size="12"></i>
                </button>
                <div id="${msgId}-dropdown" class="dropdown-menu shadow-xl border border-slate-100 py-1 overflow-hidden">
                    <button class="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 flex items-center gap-2" onclick="downloadContent('${msgId}', 'txt')"><i data-lucide="file-text" size="10"></i> TXT</button>
                    <button class="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 flex items-center gap-2" onclick="downloadContent('${msgId}', 'pdf')"><i data-lucide="file-down" size="10"></i> PDF</button>
                    <button class="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 flex items-center gap-2" onclick="downloadContent('${msgId}', 'word')"><i data-lucide="file-type" size="10"></i> Word</button>
                </div>
            </div>
            <button class="action-btn p-1 rounded-lg" onclick="copyToClipboard(this)" title="复制">
                <i data-lucide="copy" size="12"></i>
            </button>
            <button class="action-btn p-1 rounded-lg" onclick="regenerateAnalysis()" title="重新生成">
                <i data-lucide="refresh-cw" size="12"></i>
            </button>
            <div class="h-4 w-[1px] bg-slate-200 mx-1"></div>
            <button class="action-btn p-1 rounded-lg hover:text-green-600" onclick="rateMessage(this, 'like')" title="喜欢">
                <i data-lucide="thumbs-up" size="12"></i>
            </button>
            <button class="action-btn p-1 rounded-lg hover:text-red-600" onclick="rateMessage(this, 'dislike')" title="不喜欢">
                <i data-lucide="thumbs-down" size="12"></i>
            </button>
        `;
        content.appendChild(actions);
        // Store content for downloads
        wrapper.dataset.content = msg.content;
        wrapper.id = msgId;
    }
    
    if (msg.role !== 'user') wrapper.appendChild(avatar);
    wrapper.appendChild(content);
    chatContainer.appendChild(wrapper);
    lucide.createIcons();
    scrollToBottom();
}

async function handleSendMessage(overrideText = null) {
    const text = overrideText || userInput.value.trim();
    if (!text || isAnalyzing) return;

    if (!currentChatId) {
        createNewChat();
    }

    const chat = conversations.find(c => c.id === currentChatId);
    if (chat.title === '新对话') {
        chat.title = text.length > 15 ? text.substring(0, 15) + '...' : text;
        currentChatTitle.innerText = chat.title;
    }

    const userMsg = { role: 'user', content: text };
    chat.messages.push(userMsg);
    renderMessage(userMsg);
    userInput.value = '';
    userInput.style.height = 'auto';
    
    isAnalyzing = true;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i data-lucide="square" size="16"></i>';
    lucide.createIcons();
    
    // Create AbortController for this request
    currentAbortController = new AbortController();
    
    // Thinking indicator
    const thinkingWrapper = document.createElement('div');
    thinkingWrapper.id = 'thinking-indicator';
    thinkingWrapper.className = 'max-w-4xl mx-auto flex gap-4 justify-start';
    thinkingWrapper.innerHTML = `
        <div class="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0 mt-1">
            <i data-lucide="brain-circuit" size="16" class="animate-pulse"></i>
        </div>
        <div class="chat-bubble-assistant p-4 text-sm text-slate-400 font-medium">
            FinMind 正在深度分析中<span class="loading-dots"></span>
        </div>
    `;
    chatContainer.appendChild(thinkingWrapper);
    lucide.createIcons();
    scrollToBottom();

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text }),
            signal: currentAbortController.signal
        });
        
        const result = await response.json();
        thinkingWrapper.remove();
        
        if (result.status === 'success') {
            const assistantMsg = { 
                role: 'assistant', 
                content: result.report
            };
            chat.messages.push(assistantMsg);
            renderMessage(assistantMsg);
        } else {
            const errorMsg = { role: 'assistant', content: '❌ 分析失败：' + (result.error || '连接超时') };
            chat.messages.push(errorMsg);
            renderMessage(errorMsg);
        }
    } catch (err) {
        if (document.getElementById('thinking-indicator')) thinkingWrapper.remove();
        if (err.name === 'AbortError') {
            const cancelMsg = { role: 'assistant', content: '⚠️ 已取消分析。' };
            chat.messages.push(cancelMsg);
            renderMessage(cancelMsg);
        } else {
            const errorMsg = { role: 'assistant', content: '❌ 无法连接服务器，请检查后端状态。' };
            chat.messages.push(errorMsg);
            renderMessage(errorMsg);
        }
    } finally {
        isAnalyzing = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i data-lucide="arrow-up" size="20"></i>';
        lucide.createIcons();
        currentAbortController = null;
        saveConversations();
        updateHistoryUI();
    }
}

function scrollToBottom() {
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
}

// Interactive Features
window.toggleDownloadDropdown = function(msgId) {
    const dropdown = document.getElementById(`${msgId}-dropdown`);
    document.querySelectorAll('.dropdown-menu').forEach(el => {
        if (el !== dropdown) el.classList.remove('show');
    });
    dropdown.classList.toggle('show');
    
    // Close on click outside
    const closeHandler = (e) => {
        if (!dropdown.contains(e.target) && !e.target.closest('button')) {
            dropdown.classList.remove('show');
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 10);
};

window.downloadContent = function(msgId, format) {
    const wrapper = document.getElementById(msgId);
    const content = wrapper.querySelector('.chat-bubble-assistant').innerText;
    const filename = `FinMind_Report_${new Date().getTime()}`;

    if (format === 'txt') {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.txt`;
        a.click();
    } else if (format === 'pdf') {
        // Use a simpler approach for PDF with better Chinese support
        // We'll create a temporary hidden element to print, which handles system fonts better
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>${filename}</title>
                    <style>
                        body { font-family: "Microsoft YaHei", "SimSun", sans-serif; padding: 40px; line-height: 1.6; }
                        pre { white-space: pre-wrap; word-wrap: break-word; }
                        h1 { text-align: center; }
                    </style>
                </head>
                <body>
                    <h1>FinMind 金融分析报告</h1>
                    <pre>${content}</pre>
                </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    } else if (format === 'word') {
        const blob = new Blob(['\ufeff' + content], { type: 'application/msword' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.doc`;
        a.click();
    }
};

window.copyToClipboard = function(btn) {
    const content = btn.closest('.flex-col').querySelector('.chat-bubble-assistant').innerText;
    navigator.clipboard.writeText(content).then(() => {
        // Show toast
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
        
        // Button feedback
        const icon = btn.querySelector('i');
        const originalIcon = icon.getAttribute('data-lucide');
        icon.setAttribute('data-lucide', 'check');
        lucide.createIcons();
        btn.classList.add('text-green-500');
        setTimeout(() => {
            icon.setAttribute('data-lucide', originalIcon);
            lucide.createIcons();
            btn.classList.remove('text-green-500');
        }, 2000);
    });
};

window.regenerateAnalysis = function() {
    if (isAnalyzing) return;
    const currentChat = conversations.find(c => c.id === currentChatId);
    if (!currentChat) return;
    const lastUserMsg = [...currentChat.messages].reverse().find(m => m.role === 'user');
    if (lastUserMsg) handleSendMessage(lastUserMsg.content);
};

window.rateMessage = function(btn, type) {
    btn.classList.toggle(type === 'like' ? 'text-green-600' : 'text-red-600');
    const otherBtn = type === 'like' ? btn.nextElementSibling : btn.previousElementSibling;
    otherBtn.classList.remove(type === 'like' ? 'text-red-600' : 'text-green-600');
};

// Event Listeners
sendBtn.addEventListener('click', () => {
    if (isAnalyzing && currentAbortController) {
        currentAbortController.abort();
    } else {
        handleSendMessage();
    }
});
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
});

newChatBtn.addEventListener('click', createNewChat);

toggleSidebarBtn.addEventListener('click', () => {
    sidebar.classList.toggle('-translate-x-full');
});

// Suggestions
document.querySelectorAll('.suggestion-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const textElement = btn.querySelector('.font-medium');
        if (textElement) {
            userInput.value = textElement.innerText;
            handleSendMessage();
        }
    });
});

// Initial load
if (conversations.length > 0) {
    loadChat(conversations[0].id);
} else {
    currentChatTitle.innerText = '新对话';
    updateHistoryUI();
}
