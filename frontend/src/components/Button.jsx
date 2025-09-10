import * as React from 'react';
import Button from '@mui/material/Button';

export default function ButtonUsage({onClick}) {
    return <Button onClick={onClick} variant="contained">Data Table</Button>;
}