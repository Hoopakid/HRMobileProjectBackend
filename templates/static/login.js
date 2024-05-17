document.getElementById('login_form').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    fetch('http://127.0.0.1:8000/admin/login', {
        method: 'POST',
        headers: {
            accept: 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email.value,
            password: password.value
        })
    })
        .then(response => response.json())
        .then(res => {
            setCookie(res.access_token, res.refresh_token)
            // window.location.href = 'dashboard.html'
            window.location.replace('dashboard.html')
        })
})
const setCookie = (access_token, refresh_token) => {
    document.cookie = `access_token=${access_token}; path=/;`
    document.cookie = `refresh_token=${refresh_token}; path=/;`
}


function getCookie(key) {
    const cookies = document.cookie.split('; ');
    const cookie = cookies.find(c => c.startsWith(`${key}=`));
    if (!cookie) return undefined;
    return cookie.split('=')[1];
}