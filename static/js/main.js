document.addEventListener('DOMContentLoaded', function () {
  // Toggle password on Register page
  const toggle = document.getElementById('togglePassword');
  const pwd = document.getElementById('password');

  if (toggle && pwd) {
    const toggleFn = () => {
      const show = pwd.type === 'password';
      pwd.type = show ? 'text' : 'password';
      toggle.textContent = show ? 'visibility' : 'visibility_off';
    };
    toggle.addEventListener('click', toggleFn);
    toggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleFn();
      }
    });

    // Simple password strength hint
    const strengthEl = document.getElementById('passwordStrength');
    const checkStrength = (v) => {
      let score = 0;
      if (v.length >= 8) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[a-z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      if (strengthEl) {
        const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
        const idx = Math.min(score - 1, 4);
        strengthEl.textContent = v ? `Strength: ${labels[idx >= 0 ? idx : 0]}` : '';
      }
    };
    pwd.addEventListener('input', (e) => checkStrength(e.target.value));
  }

  // Toggle password on Login page
  const toggleLogin = document.getElementById('togglePasswordLogin');
  const loginPwd = document.getElementById('login_password');
  if (toggleLogin && loginPwd) {
    const toggleFn2 = () => {
      const show = loginPwd.type === 'password';
      loginPwd.type = show ? 'text' : 'password';
      toggleLogin.textContent = show ? 'visibility' : 'visibility_off';
    };
    toggleLogin.addEventListener('click', toggleFn2);
    toggleLogin.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleFn2();
      }
    });
  }
});
