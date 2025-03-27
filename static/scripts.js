async function addQuote() {
    const form = document.getElementById('addQuoteForm');
    const formData = new FormData(form);

    try {
        const response = await fetch('/add_quote', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            console.log(data.message);
            fetchAndUpdateQuotes();
            form.reset();
        } else {
            const errorData = await response.json();
            console.error('Ошибка добавления цитаты:', errorData.error);
            alert('Не удалось добавить цитату: ' + errorData.error);
        }
    } catch (error) {
        console.error('Сетевая ошибка:', error);
        alert('Произошла сетевая ошибка.');
    }
}

async function deleteQuote() {
    const form = document.getElementById('deleteQuoteForm');
    const formData = new FormData(form);

    try {
        const response = await fetch('/delete_quote', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            console.log(data.message);
            fetchAndUpdateQuotes();
            form.reset();
        } else {
            const errorData = await response.json();
            console.error('Ошибка удаления цитаты:', errorData.error);
            alert('Не удалось удалить цитату: ' + errorData.error);
        }
    } catch (error) {
        console.error('Сетевая ошибка:', error);
        alert('Произошла сетевая ошибка.');
    }
}

async function fetchAndUpdateQuotes() {
    try {
        const response = await fetch('/get_quotes');
        if (response.ok) {
            const data = await response.json();
            const quotesContainer = document.getElementById('quotesContainer');
            quotesContainer.innerHTML = '';

            if (data.quotes && data.quotes.length > 0) {
                const table = document.createElement('table');
                const thead = document.createElement('thead');
                const tbody = document.createElement('tbody');

                const headerRow = document.createElement('tr');
                ['Цитата', 'Автор', 'Дата добавления'].forEach(headerText => {
                    const th = document.createElement('th');
                    th.textContent = headerText;
                    headerRow.appendChild(th);
                });
                thead.appendChild(headerRow);
                table.appendChild(thead);

                data.quotes.forEach(quote => {
                    const row = document.createElement('tr');
                    const quoteCell = document.createElement('td');
                    quoteCell.textContent = quote.quote;
                    const authorCell = document.createElement('td');
                    authorCell.textContent = quote.author;
                    const dateCell = document.createElement('td');
                    dateCell.textContent = quote.dateOfadd;
                    row.appendChild(quoteCell);
                    row.appendChild(authorCell);
                    row.appendChild(dateCell);
                    tbody.appendChild(row);
                });
                table.appendChild(tbody);
                quotesContainer.appendChild(table);
            } else {
                quotesContainer.innerHTML = '<p>Нет доступных цитат.</p>';
            }
        } else {
            console.error('Ошибка при получении цитат:', response.status);
        }
    } catch (error) {
        console.error('Сетевая ошибка при получении цитат:', error);
    }
}

window.onload = fetchAndUpdateQuotes;