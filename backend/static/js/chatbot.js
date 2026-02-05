const userInput = document.getElementById("userMessage");
const chatWindow = document.getElementById("chatbotMessages");

let complaintMode = false;
let waitingForEmail = false;
let complaintText = "";

// ✅ Sound Effects (with error handling)
let sendSound, receiveSound;
try {
  sendSound = new Audio("/static/sounds/send.mp3");
  receiveSound = new Audio("/static/sounds/receive.mp3");
  // Set volume to prevent loud sounds
  sendSound.volume = 0.3;
  receiveSound.volume = 0.3;
} catch (e) {
  console.log("Sound files not found, continuing without audio");
  sendSound = { play: () => {} };
  receiveSound = { play: () => {} };
}

// ✅ Enhanced FAQ buttons with all options
window.onload = function () {
  const faqList = [
    "How do I vote?",
    "How to register for voting?",
    "What is a Halka?",
    "I have a complaint",
    "Check my complaint status"
  ];
  
  const faqWrapper = document.createElement("div");
  faqWrapper.className = "faq-buttons";

  faqList.forEach(text => {
    const btn = document.createElement("button");
    btn.innerText = text;
    btn.className = "faq-btn";
    btn.onclick = () => {
      // Reset any ongoing complaint processes
      complaintMode = false;
      waitingForEmail = false;
      
      userInput.value = text;
      sendMessage();
    };
    faqWrapper.appendChild(btn);
  });
  
  chatWindow.prepend(faqWrapper);
  
  // Welcome message
  setTimeout(() => {
    appendMessage("bot", "Hi! I'm VotoBot, your Votonomy assistant. I can help you with voting, registration, Pakistan information, and handling complaints. Click a button or ask me anything!");
  }, 500);
};

// ✅ Toggle Chatbot with animation
function toggleChatbot() {
  const chatbot = document.getElementById("chatbotWindow");
  const icon = document.querySelector(".chatbot-icon");
  
  if (chatbot.style.display === "block") {
    chatbot.style.display = "none";
    icon.style.transform = "scale(1)";
  } else {
    chatbot.style.display = "block";
    icon.style.transform = "scale(1.1)";
    // Focus on input when opening
    setTimeout(() => userInput.focus(), 100);
  }
}

// ✅ Enhanced Send Message Function
function sendMessage() {
  const message = userInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  userInput.value = "";
  sendSound.play();
  showTyping();

  // ✅ Send ALL messages to backend - let backend handle complaint workflow
  fetch("/chatbot/message", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    },
    body: JSON.stringify({ message: message })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      removeTyping();
      const reply = data.reply;
      receiveSound.play();
      appendMessage("bot", reply);
    })
    .catch(error => {
      removeTyping();
      console.error("Chat error:", error);
      appendMessage("bot", "❌ Sorry, I'm having trouble connecting. Please check your internet connection and try again.");
    });
}

// ✅ Enhanced Message Display with Rich Formatting
function appendMessage(sender, text) {
  const wrapper = document.createElement("div");
  wrapper.className = sender;
  wrapper.style.cssText = `
    margin-bottom: 12px;
    display: flex;
    ${sender === 'user' ? 'justify-content: flex-end;' : 'justify-content: flex-start;'}
    align-items: flex-start;
    gap: 8px;
  `;

  const msg = document.createElement("div");
  msg.className = "message";
  msg.style.cssText = `
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 18px;
    font-size: 14px;
    line-height: 1.4;
    word-wrap: break-word;
    ${sender === 'user' ? 
      'background: #00b894; color: white; border-bottom-right-radius: 4px;' : 
      'background: #f8f9fa; color: #333; border-bottom-left-radius: 4px; border: 1px solid #e9ecef;'
    }
  `;
  
  // ✅ Handle formatted text (especially for complaint status responses)
  if (text.includes("**") || text.includes("\n")) {
    // Convert markdown-style formatting to HTML
    let formattedText = text
      .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #00b894;">$1</strong>')  // Bold text in green
      .replace(/\n/g, '<br>')  // Line breaks
      .replace(/📄|⏳|🔄|✅|❌|📋/g, '<span style="font-size: 16px;">$&</span>');  // Larger emojis
    msg.innerHTML = formattedText;
  } else {
    msg.textContent = text;
  }

  const time = document.createElement("div");
  time.className = "timestamp";
  time.style.cssText = `
    font-size: 11px;
    color: #999;
    margin-top: 4px;
    text-align: ${sender === 'user' ? 'right' : 'left'};
  `;
  time.textContent = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });

  // ✅ Bot avatar with fallback
  if (sender === "bot") {
    const avatar = document.createElement("div");
    avatar.style.cssText = `
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: linear-gradient(135deg, #00b894, #00a085);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 14px;
      flex-shrink: 0;
    `;
    avatar.textContent = "🤖";
    wrapper.appendChild(avatar);
  }

  const messageContainer = document.createElement("div");
  messageContainer.appendChild(msg);
  messageContainer.appendChild(time);
  wrapper.appendChild(messageContainer);
  
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  
  // ✅ Auto-scroll animation
  wrapper.style.opacity = "0";
  wrapper.style.transform = "translateY(20px)";
  setTimeout(() => {
    wrapper.style.transition = "all 0.3s ease";
    wrapper.style.opacity = "1";
    wrapper.style.transform = "translateY(0)";
  }, 50);
}

// ✅ Enhanced Typing Indicator - FIXED to ensure clean removal
function showTyping() {
  // Remove any existing typing indicator first
  removeTyping();
  
  const typing = document.createElement("div");
  typing.id = "typing";
  typing.className = "bot typing";
  typing.style.cssText = `
    margin-bottom: 12px;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 8px;
  `;

  const avatar = document.createElement("div");
  avatar.style.cssText = `
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #00b894, #00a085);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 14px;
  `;
  avatar.textContent = "🤖";

  const dots = document.createElement("div");
  dots.className = "dot-flashing";
  dots.style.cssText = `
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 18px;
    padding: 10px 14px;
    display: flex;
    gap: 4px;
    align-items: center;
  `;
  
  // Create animated dots
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("div");
    dot.className = "typing-dot";
    dot.style.cssText = `
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #00b894;
      animation: typing 1.4s infinite;
      animation-delay: ${i * 0.2}s;
    `;
    dots.appendChild(dot);
  }

  typing.appendChild(avatar);
  typing.appendChild(dots);
  chatWindow.appendChild(typing);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  // Add CSS animation if not exists
  if (!document.getElementById("typing-animation")) {
    const style = document.createElement("style");
    style.id = "typing-animation";
    style.textContent = `
      @keyframes typing {
        0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
        30% { opacity: 1; transform: scale(1); }
      }
    `;
    document.head.appendChild(style);
  }
}

// ✅ Remove Typing Indicator - FIXED to stop animation immediately
function removeTyping() {
  const typing = document.getElementById("typing");
  if (typing) {
    // Stop all animations on the typing indicator and its children
    const dots = typing.querySelectorAll('.typing-dot');
    dots.forEach(dot => {
      dot.style.animation = 'none';
      dot.style.opacity = '0';
    });
    
    const dotFlashing = typing.querySelector('.dot-flashing');
    if (dotFlashing) {
      dotFlashing.style.animation = 'none';
    }
    
    // Immediately remove the element without transition
    typing.remove();
  }
}

// ✅ Enhanced Complaint Submission
function submitComplaint(email, text) {
  showTyping();
  
  fetch("/chatbot/submit-complaint", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    },
    body: JSON.stringify({ email: email, text: text })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      removeTyping();
      receiveSound.play();
      appendMessage("bot", data.reply);
      
      // ✅ Clear complaint modes after successful submission
      complaintMode = false;
      waitingForEmail = false;
      
      // If successful, show helpful follow-up
      if (data.reply.includes("✅") && data.reply.includes("registered")) {
        setTimeout(() => {
          appendMessage("bot", "💡 You can check your complaint status anytime by clicking 'Check my complaint status' or typing your complaint ID.");
        }, 2000);
      }
    })
    .catch(error => {
      removeTyping();
      console.error("Complaint submission error:", error);
      appendMessage("bot", "❌ Error submitting complaint. Please check your internet connection and try again.");
      
      // Reset modes on error too
      complaintMode = false;
      waitingForEmail = false;
    });
}

// ✅ Enter Key Support
userInput.addEventListener("keydown", function(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

// ✅ Auto-resize input (optional enhancement)
userInput.addEventListener("input", function() {
  this.style.height = "auto";
  this.style.height = (this.scrollHeight) + "px";
});

// ✅ Clear chat function (optional - can be called from console)
function clearChat() {
  const messages = chatWindow.querySelectorAll('.user, .bot:not(.faq-buttons)');
  messages.forEach(msg => msg.remove());
  appendMessage("bot", "Chat cleared! How can I help you with Votonomy or Pakistan?");
}

// ✅ Initialize chatbot state
document.addEventListener("DOMContentLoaded", function() {
  // Set initial input placeholder
  if (userInput) {
    userInput.placeholder = "Ask about voting, registration, or Pakistan...";
    userInput.style.cssText = `
      border-radius: 20px;
      border: 2px solid #e9ecef;
      padding: 10px 15px;
      transition: all 0.3s ease;
    `;
    
    // Focus effects
    userInput.addEventListener("focus", function() {
      this.style.borderColor = "#00b894";
      this.style.boxShadow = "0 0 0 3px rgba(0, 184, 148, 0.1)";
    });
    
    userInput.addEventListener("blur", function() {
      this.style.borderColor = "#e9ecef";
      this.style.boxShadow = "none";
    });
  }
  
  // ✅ Fix cursor for close button and other interactive elements
  const chatbotHeader = document.querySelector('.chatbot-header');
  if (chatbotHeader) {
    const closeButton = chatbotHeader.querySelector('span');
    if (closeButton) {
      closeButton.style.cursor = 'pointer';
      closeButton.addEventListener('mouseenter', function() {
        this.style.cursor = 'pointer';
      });
    }
  }
  
  // ✅ Fix cursor for chatbot icon
  const chatbotIcon = document.querySelector('.chatbot-icon');
  if (chatbotIcon) {
    chatbotIcon.style.cursor = 'pointer';
    chatbotIcon.addEventListener('mouseenter', function() {
      this.style.cursor = 'pointer';
    });
  }
  
  // ✅ Add global styles to fix cursor issues
  const style = document.createElement('style');
  style.textContent = `
    .chatbot-icon, .chatbot-header span, .faq-btn, button {
      cursor: pointer !important;
    }
    .chatbot-window, .chatbot-header, .chatbot-body, .message {
      cursor: default !important;
    }
    .chatbot-input input {
      cursor: text !important;
    }
  `;
  document.head.appendChild(style);
  
  console.log("🤖 VotoBot initialized successfully!");
});