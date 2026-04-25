document.addEventListener('DOMContentLoaded', () => {
    const copyBtn = document.getElementById('copyBtn');
    const configCode = document.getElementById('configCode');

    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(configCode.innerText);
            
            // Visual feedback
            const originalText = copyBtn.innerText;
            copyBtn.innerText = 'Copied!';
            copyBtn.style.backgroundColor = 'rgba(124, 58, 237, 0.4)';
            copyBtn.style.borderColor = 'var(--primary)';
            
            setTimeout(() => {
                copyBtn.innerText = originalText;
                copyBtn.style.backgroundColor = 'var(--glass-bg)';
                copyBtn.style.borderColor = 'var(--glass-border)';
            }, 2000);
            
        } catch (err) {
            console.error('Failed to copy text: ', err);
            copyBtn.innerText = 'Failed';
        }
    });
});
