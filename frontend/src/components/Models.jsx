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


const MODEL_API_URL = 'http://localhost:8000/models/';

const Models = () => {
    const [options, setOptions] = useState([]); // flattened grouped options
    const [loading, setLoading] = useState(false);

    const manufacturersAll = useContext(ManufacturersContext);
    const {selectedManufacturers} = useContext(SelectedManufacturersContext); // now array of ids
    const {selectedModels, setSelectedModels} = useContext(SelectedModelsContext);

    // Build lookup for manufacturer text
    const mLookup = React.useMemo(() => {
        const map = {};
        (manufacturersAll || []).forEach(m => { map[m.value] = m.text; });
        return map;
    }, [manufacturersAll]);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            if (!Array.isArray(selectedManufacturers) || selectedManufacturers.length === 0) {
                setOptions([]);
                setSelectedModels([]);
                return;
            }
            setLoading(true);
            try {
                const promises = selectedManufacturers.map(id => fetch(MODEL_API_URL + id).then(r => r.json()).then(list => ({ id, list })));
                const results = await Promise.all(promises);
                if (cancelled) return;
                const merged = [];
                results.forEach(({ id, list }) => {
                    if (Array.isArray(list)) {
                        list.forEach(model => {
                            // Ensure each model object has unique composite key & group
                            merged.push({
                                ...model,
                                manufacturerId: id,
                                group: mLookup[id] || id,
                                compositeValue: `${id}:${model.value}`
                            });
                        });
                    }
                });
                setOptions(merged);
            } catch (_) {
                if (!cancelled) setOptions([]);
            } finally {
                if (!cancelled) setLoading(false);
            }
        }
        load();
        return () => { cancelled = true; };
    }, [selectedManufacturers, mLookup, setSelectedModels]);

    const handleChange = (event, selectedOptionObjects) => {
        // store array of composite ids or original model ids? Use composite to avoid clashes
        const ids = selectedOptionObjects.map(o => o.compositeValue);
        setSelectedModels(ids);
    };

    // Derive value objects from stored selectedModels
    const valueObjects = Array.isArray(selectedModels)
        ? options.filter(opt => selectedModels.includes(opt.compositeValue))
        : [];

    return (
        <Stack spacing={2}>
            <Autocomplete
                multiple
                id="models-multi-grouped"
                options={options}
                disableCloseOnSelect
                loading={loading}
                groupBy={(option) => option.group}
                value={valueObjects}
                onChange={handleChange}
                getOptionLabel={(option) => option.text}
                isOptionEqualToValue={(o, v) => o.compositeValue === v.compositeValue}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        label="Models"
                        placeholder={loading ? 'Loading…' : 'Select models'}
                    />
                )}
            />
        </Stack>
    );
}

export default Models;