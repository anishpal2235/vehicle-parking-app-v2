// Parking App JavaScript

// Check if service worker is supported
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/service-worker.js')
      .then(registration => {
        console.log('Service Worker registered with scope:', registration.scope);
      })
      .catch(error => {
        console.error('Service Worker registration failed:', error);
      });
  });
}

// Variables for PWA installation
let deferredPrompt;
const installBanner = document.getElementById('install-banner');
const installButton = document.getElementById('install-button');
const closeInstallButton = document.getElementById('close-install-banner');

// Detect if app can be installed
window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent Chrome 76+ from automatically showing the prompt
  e.preventDefault();
  
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  
  // Show the install banner
  if (installBanner) {
    installBanner.classList.add('show');
  }
});

// Install button click handler
if (installButton) {
  installButton.addEventListener('click', () => {
    // Hide the install banner
    installBanner.classList.remove('show');
    
    // Show the browser install prompt
    deferredPrompt.prompt();
    
    // Wait for the user to respond to the prompt
    deferredPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('User accepted the install prompt');
      } else {
        console.log('User dismissed the install prompt');
      }
      
      // Clear the deferredPrompt variable
      deferredPrompt = null;
    });
  });
}

// Close install banner button
if (closeInstallButton) {
  closeInstallButton.addEventListener('click', () => {
    installBanner.classList.remove('show');
  });
}

// Hide install banner if app is already installed
window.addEventListener('appinstalled', (evt) => {
  if (installBanner) {
    installBanner.classList.remove('show');
  }
  console.log('App installed');
});

// Handle dark mode
const darkModeToggle = document.getElementById('dark-mode-toggle');
const body = document.body;

// Check if dark mode is preferred
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
  body.classList.add('dark-mode-enabled');
}

// Listen for dark mode preference change
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
  if (e.matches) {
    body.classList.add('dark-mode-enabled');
  } else {
    body.classList.remove('dark-mode-enabled');
  }
});

// Dark mode toggle
if (darkModeToggle) {
  darkModeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode-enabled');
    
    // Save preference to localStorage
    const isDarkMode = body.classList.contains('dark-mode-enabled');
    localStorage.setItem('darkMode', isDarkMode);
  });
  
  // Check if dark mode was previously enabled
  const storedDarkMode = localStorage.getItem('darkMode');
  if (storedDarkMode === 'true') {
    body.classList.add('dark-mode-enabled');
  } else if (storedDarkMode === 'false') {
    body.classList.remove('dark-mode-enabled');
  }
}

// Create responsive tables
document.addEventListener('DOMContentLoaded', () => {
  const tables = document.querySelectorAll('table');
  
  tables.forEach(table => {
    // If table is not already in a responsive wrapper
    if (!table.parentElement.classList.contains('table-responsive')) {
      const wrapper = document.createElement('div');
      wrapper.classList.add('table-responsive');
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    }
  });
  
  // Set the footer year
  const yearSpan = document.querySelector('.footer .year');
  if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear();
  }
}); 