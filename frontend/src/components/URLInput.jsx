import React, {useEffect, useState} from 'react';
import Button from "@mui/material/Button";
import { api } from '../api/client';

const URLInput = () => {
    const [url, setUrl] = useState('');
    const [responseData, setResponseData] = useState(null);

    const fetchData = async () => {
        if (!url) return; // Don't make a request if URL is empty
        const queries = url.split('?')[1];
        console.log(queries)
        try {
            const response = await api.get(`/scrape/cars?${queries}`);
            setResponseData(response.data);
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        // The fetch will be triggered by the useEffect when 'url' changes
    };

    return (
        <div>
            <form onSubmit={handleSubmit}>
                <label style={{font: "1rem"}}>
                    Enter URL:
                    <input
                        type="text"
                        value={url}
                        onChange={(event) => setUrl(event.target.value)}
                    />
                </label>
                <Button onClick={fetchData} variant="outlined">Scrape</Button>
            </form>

            {responseData && (
                <div>
                    <h2>Response Data:</h2>
                    <pre>{JSON.stringify(responseData, null, 2)}</pre>
                </div>
            )}
        </div>
    );
};

export default URLInput;
