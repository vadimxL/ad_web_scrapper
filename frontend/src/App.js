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
import {QueryClient, QueryClientProvider, useQuery} from '@tanstack/react-query'
import * as PropTypes from "prop-types";
import CriteriaForm from "./components/CriteriaForm";
import Tasks from "./components/Tasks";
import AdvancedOptions from "./components/AdvancedOptions";
import CreateTask from "./components/CreateTask";

const CREATE_TASK_URL = 'http://127.0.0.1:8000/v2/tasks';


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

    const [selectedManufacturers, setSelectedManufacturers] = useState([]);
    const [selectedModels, setSelectedModels] = useState([]);

    const [tasks, setTasks] = useState([]);
    const [manufacturers, setManufacturers] = useState([]);
    const [priceRange, setPriceRange] = useState({start_price: '', end_price: '',});

    const handleInputChange = (e) => {
        const {name, value} = e.target;
        setPriceRange((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    const fetchManufacturers = () => {
        fetch("http://localhost:8000/manufacturers")
            .then((r) => r.json())
            .then((manufacturers) => setManufacturers(manufacturers));
    }

    console.log("Fetching manufacturers...." + manufacturers);
    useEffect(() => {
        fetchManufacturers();
    }, []);

    const handleSubmit = async (event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);

        const requestData = {
            email: data.get('email'),
            // manufacturers: selectedManufacturers.map((manufacturers) => manufacturers),
            manufacturer: selectedManufacturers,
            // models: selectedModels.map((models) => models),
            model: selectedModels,
            year_start: data.get('start_year'),
            year_end: data.get('end_year'),
            km_start: data.get('start_km'),
            km_end: data.get('end_km'),
            // mileage_range: {"min": "", "max": ""},
            // price_range: {"min": priceRange.start_price, "max": priceRange.end_price},
        };

        console.log(requestData);

        try {
            const response = await axios.post(CREATE_TASK_URL, requestData);
            // Handle the response as needed
            console.log(response.data);
        } catch (error) {
            // Handle errors
            console.error('Error sending POST request:', error);
        }

    };

    const handleSetTodos = (newValues) => {
        console.log("**selected tasks...." + tasks);
        setTasks(newValues);
    }

    return (
        <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={defaultTheme}>
                <Container component="main" maxWidth="xs">
                    <ManufacturersContext.Provider value={manufacturers}>
                        <SelectedManufacturersContext.Provider
                            value={{selectedManufacturers, setSelectedManufacturers}}>
                            <SelectedModelsContext.Provider value={{selectedModels, setSelectedModels}}>
                                <CriteriaForm onSubmit={handleSubmit}
                                              renderInput={(params) => <TextField {...params} />}/>
                            </SelectedModelsContext.Provider>
                        </SelectedManufacturersContext.Provider>
                    </ManufacturersContext.Provider>
                    <CssBaseline/>
                    <AdvancedOptions/>
                    {/*<CreateTask/>*/}
                    <Copyright sx={{mt: 5}}/>
                </Container>
            </ThemeProvider>
        </QueryClientProvider>
    );
}