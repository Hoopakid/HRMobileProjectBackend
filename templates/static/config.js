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