import * as React from 'react';
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { api } from '../api/client';
import {useState} from "react";


export default function CreateTask() {
    const [status, setStatus] = useState("");
    const [detail, setDetail] = useState("");

    const submitHandler = async (e) => {
        console.log('submit called');
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        const requestData = {
            email: data.get('email'),
            url: data.get('url')
        };
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            params: {
                email: requestData.email,
                url: requestData.url,
            }
        }
        try {
            const response = await api.post('/v2/tasks', requestData, config);
            setStatus(response.statusText)
            console.log(response.data);
        } catch (error) {
            setStatus(error.message);
            setDetail(error.response?.data?.detail || '');
            console.error('Error sending POST request:', error);
        }

    }

    return (
        <div>
            <Typography component="h1" variant="h5">
                Create Task
            </Typography>
            <Box component="form" onSubmit={submitHandler}>
                {/*<TextField />*/}
                <TextField
                    required
                    fullWidth
                    id="url"
                    label="Yad2 Url"
                    name="url"
                    autoComplete="url"
                />
                <TextField
                    required
                    fullWidth
                    id="email"
                    label="Email Address"
                    name="email"
                    autoComplete="email"
                />
                <Typography variant="h5" gutterBottom>
                    {status}
                </Typography>
                <Typography variant="h6" gutterBottom>
                    {detail}
                </Typography>
                <Button type="submit">Submit</Button>
            </Box>
        </div>
    );
}