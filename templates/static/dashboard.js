async function request(url, method = 'GET', headers = {}, body = null) {
    const fetchOptions = {
        method: method,
        headers: {...headers, 'Content-Type': 'application/json'},
        body: body ? JSON.stringify(body) : null
    };

    let response = await fetch(url, fetchOptions);
    let data = await response.json();

    if (response.ok) {
        return data;
    } else if (data['detail'] && data['messages']) {
        return handleTokenRefresh(url, method, headers, body);
    } else {
        throw new Error(data.detail || "An error occurred");
    }
}

async function handleTokenRefresh(url, method, headers, body) {
    const formData = new FormData();
    formData.append('refresh', getCookie('refresh'));

    const response = await fetch(`${BASE_URL}/api/token/refresh/`, {
        method: 'POST',
        body: formData
    });
    const data = await response.json();

    if (!response.ok || !data['access']) {
        window.location.replace('/login');
        return;
    }

    setCookie('access', data['access'], 1);
    headers['Authorization'] = `Bearer ${data['access']}`;
    return request(url, method, headers, body);
}

async function main() {
    const url = 'http://localhost:8000/mobile/dashboard-api';
    try {
        const data = await request(url, 'GET', {
            'Authorization': `Bearer ${getCookie('access')}`
        });
        console.log(data);

        const chartElement = document.getElementById('myChart');
        if (chartElement) {
            const ctx = chartElement.getContext('2d');
            const myChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: Object.keys(data),
                    datasets: [{
                        label: 'Lavozimlar Soni',
                        data: Object.values(data),
                        backgroundColor: [
                            'rgba(0, 128, 0, 0.7)',
                            'rgba(0, 128, 0, 0.3)',
                            'rgba(0, 128, 0, 0.2)',
                            'rgba(0, 128, 0, 0.1)'
                        ],
                        borderColor: 'rgba(255, 255, 255, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                font: {
                                    size: 14
                                }
                            }
                        }
                    }
                }
            });
        }

    } catch (error) {
        console.error(error);
    }
}

