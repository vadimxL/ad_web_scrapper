import React, { useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { createTheme, ThemeProvider } from '@mui/material/styles';


const DataTable = () => {
    const [data, setData] = useState([]);

    const fetchData = async () => {
        try {
            const response = await fetch('http://127.0.0.1:8000/ads');
            const jsonData = await response.json();
            // Convert dictionary values to an array for mapping
            const dataArray = Object.values(jsonData?.ads || {});
            setData(dataArray);
        } catch (error) {
            console.error('Error fetching data:', error);
            setData([]); // Set empty array in case of error
        }
    };

    useEffect(() => {
        fetchData().then(r => console.log('Data fetched'));
    }, []);

    const columns = [
        { field: 'id', headerName: 'ID', width: 90 },
        { field: 'city', headerName: 'City', width: 130 },
        { field: 'manufacturer_he', headerName: 'Manufacturer', width: 130 },
        { field: 'car_model', headerName: 'Model', width: 300 },
        {
            field: 'year',
            headerName: 'Year',
            // type: 'date',
            width: 90,
        },
        {
            field: 'kilometers',
            headerName: 'Mileage',
            description: 'This column has a value getter and is not sortable.',
            width: 160,
        },
    ];


    return (
        <div style={{ height: 800, width: '100%' }}>
            <DataGrid
                sx={{
                    color: 'white',
                    boxShadow: 2,
                    border: 2,
                    borderColor: 'primary.light',
                    '& .MuiDataGrid-cell:hover': {
                        color: 'primary.main',
                    },
                }}
                rows={data}
                columns={columns}
                initialState={{
                    pagination: {
                        paginationModel: { page: 0, pageSize: 20 },
                    },
                }}
                pageSizeOptions={[5, 10]}
                checkboxSelection
            />
        </div>
    );
};

export default DataTable;
