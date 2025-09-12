import {
    Stack,
    TextField
} from "@mui/material";
import Chip from "@mui/material/Chip";
import React, {useContext, useEffect, useState} from "react";
import {
    useQueries,
} from '@tanstack/react-query'
import {ManufacturersContext, SelectedManufacturersContext, SelectedModelsContext} from "../App";
import Autocomplete from "@mui/material/Autocomplete";


const MODEL_API_URL = 'http://127.0.0.1:8000/models/';


const Models = () => {
    const [models, setModels] = useState([]);

    const {selectedManufacturers, setSelectedManufacturers} = useContext(SelectedManufacturersContext);
    const {selectedModels, setSelectedModels} = useContext(SelectedModelsContext);

    const fetchModels = () => {
        fetch(MODEL_API_URL + selectedManufacturers)
            .then((r) => r.json())
            .then((model) => setModels(model));
    }

    const handleChange = (event, data) => {
        console.log("Selected manufacturer.text: ", data);
        console.log("Selected manufacturer.value: ", data.value);
        setSelectedModels(data.value);
    };

    console.log("Fetching models...." + models);
    useEffect(() => {
        fetchModels();
    }, [selectedManufacturers]);

    return (
        <Stack spacing={2}>
            <Autocomplete
                freeSolo
                id="free-solo-2-demo"
                disableClearable
                onChange={handleChange}
                options={models}
                getOptionLabel={(models) => models.text}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        label="Search Models"
                        slotProps={{
                            input: {
                                ...params.InputProps,
                                type: 'search',
                            },
                        }}
                    />
                )}
            />
        </Stack>
    );
}

export default Models;