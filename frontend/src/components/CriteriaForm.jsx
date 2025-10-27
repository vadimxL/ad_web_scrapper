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
import Button from "@mui/material/Button";
import * as React from "react";
import Navbar from "../Navbar";
import dayjs from "dayjs";
import Slider from '@mui/material/Slider';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';

export default function CriteriaForm(props) {
    const [kmStart, setKmStart] = React.useState(0);
    const [kmEnd, setKmEnd] = React.useState(100000);
    const [yearStart, setYearStart] = React.useState(2020);
    const currentYear = new Date().getFullYear();
    const [yearEnd, setYearEnd] = React.useState(currentYear);
    const [priceRange, setPriceRange] = React.useState([0, 250000]); // [min, max]
    // Engine volume range (cc)
    const [engineVolStart, setEngineVolStart] = React.useState(800);
    const [engineVolEnd, setEngineVolEnd] = React.useState(4000);
    // Constants
    const MIN_PRICE = 0;
    const MAX_PRICE = 250000;
    const PRICE_STEP = 1000;
    const MIN_KM = 0;
    const MAX_KM = 150000;
    const KM_STEP = 1000;
    const MIN_ENGINE_VOL = 600; // cc
    const MAX_ENGINE_VOL = 6000; // cc
    const ENGINE_VOL_STEP = 100;
    // Use props for manufacturers/models selection
    const { selectedManufacturers, selectedModels } = props;

    // Determine if submit should be disabled (handle both array or scalar values)
    const hasManufacturer = Array.isArray(selectedManufacturers) ? selectedManufacturers.length > 0 : !!selectedManufacturers;
    const hasModel = Array.isArray(selectedModels) ? selectedModels.length > 0 : !!selectedModels;
    const isSubmitDisabled = !(hasManufacturer && hasModel);

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
            <Box component="form" noValidate onSubmit={e => {
                e.preventDefault();
                if (props.onSubmit) {
                    props.onSubmit({
                        manufacturer: selectedManufacturers,
                        model: selectedModels,
                        year_start: yearStart,
                        year_end: yearEnd,
                        kmStart,
                        kmEnd,
                        price_min: priceRange[0],
                        price_max: priceRange[1],
                        engine_vol_start: engineVolStart,
                        engine_vol_end: engineVolEnd,
                    });
                }
            }} sx={{mt: 3}}>
                <Grid container spacing={2}>
                    <Grid item xs={12}>
                        <Manufacturers/>
                    </Grid>
                    <Grid item xs={12}>
                        <Models/>
                    </Grid>
                    <Grid item xs={6}>
                        <LocalizationProvider dateAdapter={AdapterDayjs}>
                            <DatePicker
                                label="Start year"
                                id="start_year"
                                name="start_year"
                                views={["year"]}
                                value={dayjs(`${yearStart}-01-01`)}
                                onChange={date => setYearStart(date ? date.year() : 2020)}
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
                                value={dayjs(`${yearEnd}-01-01`)}
                                onChange={date => setYearEnd(date ? date.year() : currentYear)}
                                renderInput={props.renderInput}
                            />
                        </LocalizationProvider>
                    </Grid>
                    {/* Kilometer Range Section */}
                    <Grid item xs={12}>
                        <Typography variant="subtitle1" align="right" sx={{ fontWeight: 600, mb: 1 }}>קילומטראז'</Typography>
                        <Grid container spacing={2} alignItems="center" direction="row-reverse">
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Max"
                                    value={kmEnd.toLocaleString('he-IL')}
                                    onChange={(e) => {
                                        const raw = e.target.value.replace(/[^0-9]/g,'');
                                        const val = Math.min(Math.max(parseInt(raw||'0',10), kmStart), MAX_KM);
                                        setKmEnd(val);
                                    }}
                                    InputProps={{
                                        inputProps: { min: MIN_KM, max: MAX_KM, step: KM_STEP }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Min"
                                    value={kmStart.toLocaleString('he-IL')}
                                    onChange={(e) => {
                                        const raw = e.target.value.replace(/[^0-9]/g,'');
                                        const val = Math.max(Math.min(parseInt(raw||'0',10), kmEnd), MIN_KM);
                                        setKmStart(val);
                                    }}
                                    InputProps={{
                                        inputProps: { min: MIN_KM, max: MAX_KM, step: KM_STEP }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <Box sx={{ px: 1 }}>
                                    <Slider
                                        value={[kmStart, kmEnd]}
                                        onChange={(e, newVal) => { setKmStart(newVal[0]); setKmEnd(newVal[1]); }}
                                        valueLabelDisplay="auto"
                                        min={MIN_KM}
                                        max={MAX_KM}
                                        step={KM_STEP}
                                        getAriaLabel={() => 'Kilometer range'}
                                        valueLabelFormat={(v) => v.toLocaleString('he-IL')}
                                        disableSwap
                                    />
                                </Box>
                            </Grid>
                        </Grid>
                    </Grid>
                    {/* Price Range Section */}
                    <Grid item xs={12}>
                        <Typography variant="subtitle1" align="right" sx={{ fontWeight: 600, mb: 1 }}>מחיר</Typography>
                        <Grid container spacing={2} alignItems="center" direction="row-reverse">
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Max"
                                    value={priceRange[1]}
                                    onChange={(e) => {
                                        const v = Math.min(Math.max(parseInt(e.target.value.replace(/[^0-9]/g, '') || '0', 10), priceRange[0]), MAX_PRICE);
                                        setPriceRange([priceRange[0], v]);
                                    }}
                                    InputProps={{
                                        startAdornment: <InputAdornment position="start">₪</InputAdornment>,
                                        inputProps: { min: MIN_PRICE, max: MAX_PRICE, step: PRICE_STEP }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Min"
                                    value={priceRange[0]}
                                    onChange={(e) => {
                                        const v = Math.max(Math.min(parseInt(e.target.value.replace(/[^0-9]/g, '') || '0', 10), priceRange[1]), MIN_PRICE);
                                        setPriceRange([v, priceRange[1]]);
                                    }}
                                    InputProps={{
                                        startAdornment: <InputAdornment position="start">₪</InputAdornment>,
                                        inputProps: { min: MIN_PRICE, max: MAX_PRICE, step: PRICE_STEP }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <Box sx={{ px: 1 }}>
                                    <Slider
                                        value={priceRange}
                                        onChange={(e, newVal) => setPriceRange(newVal)}
                                        valueLabelDisplay="auto"
                                        min={MIN_PRICE}
                                        max={MAX_PRICE}
                                        step={PRICE_STEP}
                                        getAriaLabel={() => 'Price range'}
                                        valueLabelFormat={(v) => `₪ ${v.toLocaleString('he-IL')}`}
                                        disableSwap
                                    />
                                </Box>
                            </Grid>
                        </Grid>
                    </Grid>
                    {/* Engine Volume Range Section */}
                    <Grid item xs={12}>
                        <Typography variant="subtitle1" align="right" sx={{ fontWeight: 600, mb: 1 }}>נפח מנוע (cc)</Typography>
                        <Grid container spacing={2} alignItems="center" direction="row-reverse">
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Max"
                                    value={engineVolEnd.toLocaleString('he-IL')}
                                    onChange={(e) => {
                                        const raw = e.target.value.replace(/[^0-9]/g,'');
                                        const val = Math.min(Math.max(parseInt(raw||'0',10), engineVolStart), MAX_ENGINE_VOL);
                                        setEngineVolEnd(val);
                                    }}
                                    InputProps={{
                                        inputProps: { min: MIN_ENGINE_VOL, max: MAX_ENGINE_VOL, step: ENGINE_VOL_STEP }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Min"
                                    value={engineVolStart.toLocaleString('he-IL')}
                                    onChange={(e) => {
                                        const raw = e.target.value.replace(/[^0-9]/g,'');
                                        const val = Math.max(Math.min(parseInt(raw||'0',10), engineVolEnd), MIN_ENGINE_VOL);
                                        setEngineVolStart(val);
                                    }}
                                    InputProps={{
                                        inputProps: { min: MIN_ENGINE_VOL, max: MAX_ENGINE_VOL, step: ENGINE_VOL_STEP }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <Box sx={{ px: 1 }}>
                                    <Slider
                                        value={[engineVolStart, engineVolEnd]}
                                        onChange={(e, newVal) => { setEngineVolStart(newVal[0]); setEngineVolEnd(newVal[1]); }}
                                        valueLabelDisplay="auto"
                                        min={MIN_ENGINE_VOL}
                                        max={MAX_ENGINE_VOL}
                                        step={ENGINE_VOL_STEP}
                                        getAriaLabel={() => 'Engine volume range'}
                                        valueLabelFormat={(v) => v.toLocaleString('he-IL') + ' cc'}
                                        disableSwap
                                    />
                                </Box>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
                <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    sx={{mt: 3, mb: 2}}
                    disabled={isSubmitDisabled}
                >
                    צור קיטריון לקבלת התראות
                </Button>
            </Box>
        </Box>
    </div>
    );
}