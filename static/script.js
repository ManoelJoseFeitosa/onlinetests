function validatePassword() {
    const passwordInput = document.getElementById('password');
    const passwordStrengthDiv = document.getElementById('password-strength');
    const password = passwordInput.value;

    if (password.length >= 6) {
        passwordStrengthDiv.textContent = 'Senha: Forte';
        passwordStrengthDiv.className = 'form-text text-success';
    } else if (password.length >= 3) {
        passwordStrengthDiv.textContent = 'Senha: Fraca';
        passwordStrengthDiv.className = 'form-text text-warning';
    } else {
        passwordStrengthDiv.textContent = '';
        passwordStrengthDiv.className = 'form-text';
    }
}

// Exemplo de função para verificar disponibilidade de nome de usuário (requisição assíncrona - não implementado no backend)
document.getElementById('username').addEventListener('blur', function() {
    const usernameInput = this.value;
    const feedbackDiv = document.getElementById('username-feedback');
    if (usernameInput) {
        // Aqui você faria uma requisição AJAX para verificar se o nome de usuário já existe no banco de dados
        // Exemplo simulado:
        setTimeout(() => {
            if (usernameInput === 'usuarioexistente') {
                feedbackDiv.textContent = 'Este nome de usuário já está em uso.';
                feedbackDiv.className = 'form-text text-danger';
            } else {
                feedbackDiv.textContent = 'Nome de usuário disponível.';
                feedbackDiv.className = 'form-text text-success';
            }
        }, 500);
    } else {
        feedbackDiv.textContent = '';
        feedbackDiv.className = 'form-text';
    }
});

document.getElementById('email').addEventListener('blur', function() {
    const emailInput = this.value;
    const feedbackDiv = document.getElementById('email-feedback');
    const emailRegex = /[^@]+@[^@]+\.[^@]+/;
    if (emailInput) {
        if (!emailRegex.test(emailInput)) {
            feedbackDiv.textContent = 'Formato de e-mail inválido.';
            feedbackDiv.className = 'form-text text-danger';
        } else {
            // Aqui você poderia fazer uma requisição AJAX para verificar se o e-mail já existe
            feedbackDiv.textContent = ''; // Removido para simplificar o exemplo
            feedbackDiv.className = 'form-text';
        }
    } else {
        feedbackDiv.textContent = '';
        feedbackDiv.className = 'form-text';
    }
});