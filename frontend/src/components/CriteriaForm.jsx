import Box from "@mui/material/Box";
import Avatar from "@mui/material/Avatar";
import {pink} from "@mui/material/colors";
import PageviewIcon from "@mui/icons-material/Pageview";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import Manufacturers from "./Manufacturers";
import Models from "./Models";
import {LocalizationProvider} from "@mui/x-date-pickers/LocalizationProvider";
import {AdapterDayjs} from "@mui/x-date-pickers/AdapterDayjs";
import {DatePicker} from "@mui/x-date-pickers/DatePicker";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Button from "@mui/material/Button";
import * as React from "react";
import Navbar from "../Navbar";
import dayjs from "dayjs";
import {InputLabel, MenuItem, Select} from "@mui/material";
import FormControl from "@mui/material/FormControl";
import SubModel from "./SubModel";

export default function CriteriaForm(props) {
    const [age, setAge] = React.useState('');

    const handleChange = (event) => {
        setAge(event.target.value);
    };

    const menu_items = [];
    for (let i = 0; i < 100000; i += 5000) {
        menu_items.push(<MenuItem key={i} value={i}>{i}</MenuItem>);
    }

    return (
    <div>
    <Navbar />
        <Box
            sx={{
                marginTop: 8,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
            }}
        >
            <Avatar sx={{bgcolor: pink[500]}}>
                <PageviewIcon/>
            </Avatar>
            <Typography component="h1" variant="h5">
                יצירת קריטריון
            </Typography>
            <Box component="form" noValidate onSubmit={props.onSubmit} sx={{mt: 3}}>
                <Grid container spacing={2}>
                    <Grid item xs={12}>
                        <Manufacturers/>
                    </Grid>
                    <Grid item xs={12}>
                        <Models/>
                    </Grid>
                    <Grid item xs={12}>
                        <SubModel/>
                    </Grid>
                    <Grid item xs={6}>
                        <LocalizationProvider dateAdapter={AdapterDayjs}>
                            <DatePicker
                                label="Start year"
                                id="start_year"
                                name="start_year"
                                views={["year"]}
                                defaultValue={dayjs('2020-01-01')}
                                renderInput={props.renderInput}
                            />
                        </LocalizationProvider>
                    </Grid>
                    <Grid item xs={6}>
                        <LocalizationProvider dateAdapter={AdapterDayjs}>
                            <DatePicker
                                label="End year"
                                id="end_year"
                                name="end_year"
                                views={["year"]}
                                defaultValue={dayjs('2024-01-01')}
                                renderInput={props.renderInput}
                            />
                        </LocalizationProvider>
                    </Grid>
                    <Grid item xs={6}>
                        <Box sx={{ minWidth: 120 }}>
                            <FormControl fullWidth>
                                <InputLabel id="demo-simple-select-label">Km Start</InputLabel>
                                <Select
                                    labelId="demo-simple-select-label"
                                    id="demo-simple-select"
                                    value={age}
                                    label="Age"
                                    onChange={handleChange}
                                >
                                    {menu_items}
                                </Select>
                            </FormControl>
                        </Box>
                        {/*<TextField id="start_km" name="start_km" defaultValue={0} label="Km Start" variant="outlined" />*/}
                    </Grid>
                    <Grid item xs={6}>
                        <Box sx={{ minWidth: 120 }}>
                            <FormControl fullWidth>
                                <InputLabel id="demo-simple-select-label">Km End</InputLabel>
                                <Select
                                    labelId="demo-simple-select-label"
                                    id="demo-simple-select"
                                    value={age}
                                    label="Age"
                                    onChange={handleChange}
                                >
                                    {menu_items}
                                </Select>
                            </FormControl>
                        </Box>
                        {/*<TextField id="end_km" name="end_km" defaultValue={80000} label="Km End" variant="outlined" />*/}
                    </Grid>
                    <Grid item xs={12}>
                        <TextField
                            required
                            fullWidth
                            id="email"
                            label="Email Address"
                            name="email"
                            autoComplete="email"
                            defaultValue={"vadimski30@gmail.com"}
                        />
                    </Grid>
                    <Grid item xs={12}>
                        <FormControlLabel
                            control={<Checkbox value="allowExtraEmails" color="primary"/>}
                            label="I want to receive updates email."
                        />
                    </Grid>
                </Grid>
                <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    sx={{mt: 3, mb: 2}}
                >
                    צור קיטריון לקבלת התראות
                </Button>
            </Box>
        </Box>
    </div>
    );
}