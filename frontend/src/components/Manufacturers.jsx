import React, {useCallback, useContext, useState} from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import {CircularProgress, Stack, TextField} from "@mui/material";
import {ManufacturersContext, SelectedManufacturersContext} from "../App";


const Manufacturers = () => {
    const manufacturers = useContext(ManufacturersContext);
    const {selectedManufacturers, setSelectedManufacturers} = useContext(SelectedManufacturersContext);

    const handleChange = (event, manufacturer) => {
        console.log("Selected manufacturer.text: ", manufacturer);
        console.log("Selected manufacturer.value: ", manufacturer.value);
        setSelectedManufacturers(manufacturer.value);
    };

    return (
        <Stack spacing={2}>
            <Autocomplete
                freeSolo
                id="free-solo-2-demo"
                disableClearable
                onChange={handleChange}
                options={manufacturers}
                getOptionLabel={(manufacturers) => manufacturers.text}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        label="Search Manufacturers"
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
};

export default Manufacturers;
