fetch('/manufacturers')
    .then(response => response.json())
    .then(data => {
        if (Array.isArray(data)) {
            const select = document.querySelector('.selectpicker');
            data.forEach(option => {
                const optionElem = document.createElement('option');
                optionElem.textContent = option;
                select.appendChild(optionElem);
            });

            // Refresh the select picker to update options
            $('.selectpicker').selectpicker('refresh');
        } else {
            console.error('Error: Data is not in the expected format.');
        }
    })
    .catch(error => console.error('Error fetching manufacturer options:', error));