document.addEventListener('DOMContentLoaded', (event) => {
    document.querySelectorAll('.copy-pre').forEach(button => {
        button.addEventListener('click', () => {
            const preElement = button.nextElementSibling;
            const textToCopy = preElement.innerText;

            navigator.clipboard.writeText(textToCopy).then(() => {
                button.classList.remove('copy-pre');
                button.classList.add('copied-pre');
                button.innerText = "Copied!";

                setTimeout(() => {
                    button.classList.remove('copied-pre');
                    button.classList.add('copy-pre');
                    button.innerText = "Copy";
                }, 2000);

            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        });
    });
});
