const manufSelect = document.getElementById('manufacturers');
const modelSelect = document.getElementById('car_model');

console.log(manufSelect)
console.log(modelSelect)

function populateModels(manufacturer) {
    // delete the current set of <option> elements out of the
    // day <select>, ready for the next set to be injected
    while (modelSelect.firstChild) {
        modelSelect.removeChild(modelSelect.firstChild);
    }

    fetch('/models/' + manufacturer)
        .then((response) => response.json())
        .then((models) => {
            for (const model of models[manufacturer]) {
                const option = document.createElement('option');
                option.textContent = model;
                modelSelect.appendChild(option);
            }
        });
}


manufSelect.onchange = () => {
    populateModels(manufSelect.value);
}

window.onload = () => {
    populateModels(manufSelect.value)
}