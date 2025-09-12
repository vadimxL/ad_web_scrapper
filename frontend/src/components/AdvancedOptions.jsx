import * as React from 'react';
import Box from '@mui/material/Box';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormHelperText from '@mui/material/FormHelperText';
import Checkbox from '@mui/material/Checkbox';

export default function AdvancedOptions() {
    const [state, setState] = React.useState({
        all: true,
        new_: false,
        price_update: false,
        private_: false,
        dealer: false,
    });

    const handleChange = (event) => {
        setState({
            ...state,
            [event.target.name]: event.target.checked,
        });
    };

    const { all, new_, price_update, private_, dealer} = state;

    return (
        <Box sx={{display: 'flex'}}>
            <FormControl sx={{m: 3}} component="fieldset" variant="standard">
                <FormLabel component="legend">סוג מודעות</FormLabel>
                <FormGroup>
                    <FormControlLabel
                        control={
                            <Checkbox checked={all} onChange={handleChange} name="all"/>
                        }
                        label="הכל"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={new_} onChange={handleChange} name="new"/>
                        }
                        label="חדשות"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={price_update} onChange={handleChange} name="price_update"/>
                        }
                        label="עדכון במחיר"
                    />
                </FormGroup>
            </FormControl>
            <FormControl sx={{m: 3}} component="fieldset" variant="standard">
                <FormLabel component="legend">סוג מוכר</FormLabel>
                <FormGroup>
                    <FormControlLabel
                        control={
                            <Checkbox checked={all} onChange={handleChange} name="all"/>
                        }
                        label="הכל"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={private_} onChange={handleChange} name="private_"/>
                        }
                        label="פרטי"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={dealer} onChange={handleChange} name="dealer"/>
                        }
                        label="סוכנות"
                    />
                </FormGroup>
            </FormControl>
            <FormControl sx={{m: 3}} component="fieldset" variant="standard">
                <FormLabel component="legend">בעלים</FormLabel>
                <FormGroup>
                    <FormControlLabel
                        control={
                            <Checkbox checked={all} onChange={handleChange} name="all"/>
                        }
                        label="הכל"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={private_} onChange={handleChange} name="private_"/>
                        }
                        label="פרטי"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={dealer} onChange={handleChange} name="dealer"/>
                        }
                        label="חברה"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox checked={dealer} onChange={handleChange} name="dealer"/>
                        }
                        label="ליסינג"
                    />
                </FormGroup>
            </FormControl>
        </Box>
    );
}
