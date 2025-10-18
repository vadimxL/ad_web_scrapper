import * as React from 'react';
import {useEffect, useState} from 'react';
import axios from 'axios';
import {createContext} from 'react';

import CssBaseline from '@mui/material/CssBaseline';
import TextField from '@mui/material/TextField';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';
import {createTheme, ThemeProvider} from '@mui/material/styles';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query'
import * as PropTypes from "prop-types";
import CriteriaForm from "./components/CriteriaForm";
import Tasks from "./components/Tasks";
import AdvancedOptions from "./components/AdvancedOptions";
import { useAuth } from './context/AuthContext';
import { api } from './api/client';

axios.defaults.withCredentials = true;


export const ManufacturersContext = createContext([]);
export const SelectedManufacturersContext = createContext(null);
export const SelectedModelsContext = createContext(null);


function Copyright(props) {
    return (
        <Typography variant="body2" color="text.secondary" align="center" {...props}>
            {'Copyright © '}
            <Link color="inherit" href="https://mui.com/">
                Your Website
            </Link>{' '}
            {new Date().getFullYear()}
            {'.'}
        </Typography>
    );
}

// TODO remove, this demo shouldn't need to reset the theme.

const defaultTheme = createTheme();
const queryClient = new QueryClient()

CriteriaForm.propTypes = {
    onSubmit: PropTypes.func,
    manufs: PropTypes.func,
    manufacturers: PropTypes.arrayOf(PropTypes.any),
    models: PropTypes.func,
    renderInput: PropTypes.func
};

export default function SignUp() {
    const { user } = useAuth();

    const [selectedManufacturers, setSelectedManufacturers] = useState([]);
    const [selectedModels, setSelectedModels] = useState([]);
    const [manufacturers, setManufacturers] = useState([]);
    const [tasksRefreshTrigger, setTasksRefreshTrigger] = useState(0);

    const fetchManufacturers = () => {
        api.get('/manufacturers')
            .then((r) => setManufacturers(r.data));
    }

    console.log("Fetching manufacturers...." + manufacturers);
    useEffect(() => {
        fetchManufacturers();
    }, []);

    const handleSubmit = async (data) => {
        if (!user || !user.email) {
            alert('You must be logged in to create a task.');
            return;
        }
        const requestData = {
            email: user.email,
            manufacturer: Array.isArray(data.manufacturer) ? data.manufacturer.join(",") : data.manufacturer,
            model: Array.isArray(data.model) ? data.model.join(",") : data.model,
            year_start: data.year_start,
            year_end: data.year_end,
            km_start: data.kmStart,
            km_end: data.kmEnd,
        };
        console.log('Submitting:', requestData);
        try {
            await api.post('/v2/tasks', requestData);
            // Trigger tasks list refresh
            setTasksRefreshTrigger(prev => prev + 1);
        } catch (error) {
            console.error('Error sending POST request:', error);
        }
    };


    return (
            <QueryClientProvider client={queryClient}>
                <ThemeProvider theme={defaultTheme}>
                    <Container component="main" maxWidth="sm" style={{ maxWidth: 600 }}>
                        <ManufacturersContext.Provider value={manufacturers}>
                            <SelectedManufacturersContext.Provider
                                value={{selectedManufacturers, setSelectedManufacturers}}>
                                <SelectedModelsContext.Provider value={{selectedModels, setSelectedModels}}>
                                    <CriteriaForm
                                        onSubmit={handleSubmit}
                                        renderInput={(params) => <TextField {...params} />}
                                        selectedManufacturers={selectedManufacturers}
                                        setSelectedManufacturers={setSelectedManufacturers}
                                        selectedModels={selectedModels}
                                        setSelectedModels={setSelectedModels}
                                    />
                                </SelectedModelsContext.Provider>
                            </SelectedManufacturersContext.Provider>
                        </ManufacturersContext.Provider>
                        <CssBaseline/>
                        <AdvancedOptions/>
                        {/*<CreateTask/>*/}
                        <Tasks refreshTrigger={tasksRefreshTrigger} />
                        <Copyright sx={{mt: 5}}/>
                    </Container>
                </ThemeProvider>
            </QueryClientProvider>
    );
}