import React, {useContext} from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import {Stack, TextField, Chip} from "@mui/material";
import {ManufacturersContext, SelectedManufacturersContext} from "../App";


const Manufacturers = () => {
    const manufacturers = useContext(ManufacturersContext);
    const {selectedManufacturers, setSelectedManufacturers} = useContext(SelectedManufacturersContext);

    const handleChange = (event, selectedOptions) => {
        if (selectedOptions.length > 4) {
            // Ignore additions beyond 4 (keep first 4)
            selectedOptions = selectedOptions.slice(0, 4);
        }
        const ids = selectedOptions.map(opt => opt.value);
        setSelectedManufacturers(ids);
    };

    // Map selected ids back to option objects for controlled value
    const valueObjects = Array.isArray(selectedManufacturers)
        ? manufacturers.filter(m => selectedManufacturers.includes(m.value))
        : [];

    return (
        <Stack spacing={2}>
            <Autocomplete
                multiple
                id="manufacturers-multi"
                options={manufacturers}
                disableCloseOnSelect
                value={valueObjects}
                onChange={handleChange}
                getOptionLabel={(option) => option.text}
                isOptionEqualToValue={(o, v) => o.value === v.value}
                getOptionDisabled={(option) => Array.isArray(selectedManufacturers) && selectedManufacturers.length >= 4 && !selectedManufacturers.includes(option.value)}
                renderTags={(tagValue, getTagProps) =>
                    tagValue.map((option, index) => (
                        <Chip
                            {...getTagProps({ index })}
                            key={option.value}
                            label={option.text}
                            size="small"
                        />
                    ))
                }
                renderInput={(params) => (
                    <TextField
                        {...params}
                        label="Manufacturers"
                        placeholder={Array.isArray(selectedManufacturers) && selectedManufacturers.length >= 4 ? "Maximum 4 selected" : "Select up to 4"}
                    />
                )}
            />
        </Stack>
    );
};

export default Manufacturers;
