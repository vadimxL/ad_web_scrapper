import {
    Stack,
    TextField
} from "@mui/material";
import React, {useContext, useEffect, useState} from "react";
import {ManufacturersContext, SelectedManufacturersContext, SelectedModelsContext} from "../App";
import Autocomplete from "@mui/material/Autocomplete";
import { api } from '../api/client';


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
                const resp = await api.get(`/models/${selectedManufacturers.join(',')}`);
                if (!cancelled) {
                    const transformed = (resp.data || []).map(item => {
                        // Derive stable value
                        const baseVal = item.value ?? item.id ?? item.text ?? item.name;
                        // Attempt to find manufacturer grouping (API structure may differ)
                        const manufacturerId = item.manufacturer?.value || item.manufacturerId || item.manufId || null;
                        const group = manufacturerId && mLookup[manufacturerId]
                            ? mLookup[manufacturerId]
                            : (item.manufacturer?.text || item.manufacturerText || '');
                        return {
                            ...item,
                            text: item.text || item.name || String(baseVal),
                            compositeValue: String(baseVal),
                            group: group || 'Models'
                        };
                    });
                    // Deduplicate by compositeValue in case backend returns duplicates
                    const seen = new Set();
                    const unique = transformed.filter(o => {
                        if (seen.has(o.compositeValue)) return false; seen.add(o.compositeValue); return true;
                    });
                    setOptions(unique);
                    // Prune selected models that are no longer present
                    setSelectedModels(prev => Array.isArray(prev) ? prev.filter(v => unique.some(o => o.compositeValue === v)) : []);
                }
            } catch (e) {
                if (!cancelled) {
                    setOptions([]);
                    setSelectedModels([]);
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }
        load();
        return () => { cancelled = true; };
    }, [selectedManufacturers, setSelectedModels, mLookup]);

    const handleChange = (event, selectedOptionObjects) => {
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
                groupBy={(option) => option.group || ''}
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