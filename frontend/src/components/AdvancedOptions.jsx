import * as React from 'react';
import Box from '@mui/material/Box';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';

export default function AdvancedOptions() {
    const [adType, setAdType] = React.useState('all');          // סוג מודעות
    const [sellerType, setSellerType] = React.useState('all');  // סוג מוכר
    const [ownerType, setOwnerType] = React.useState('all');    // בעלים

    return (
        <Box sx={{display: 'flex'}}>
            {/* Ad Types */}
            <FormControl sx={{m: 3}} component="fieldset" variant="standard">
                <FormLabel component="legend">סוג מודעות</FormLabel>
                <RadioGroup
                    value={adType}
                    onChange={(e) => setAdType(e.target.value)}
                    name="ad-types"
                >
                    <FormControlLabel value="all" control={<Radio />} label="הכל" />
                    <FormControlLabel value="new" control={<Radio />} label="חדשות" />
                    <FormControlLabel value="price_update" control={<Radio />} label="עדכון במחיר" />
                </RadioGroup>
            </FormControl>
            {/* Seller Types */}
            <FormControl sx={{m: 3}} component="fieldset" variant="standard">
                <FormLabel component="legend">סוג מוכר</FormLabel>
                <RadioGroup
                    value={sellerType}
                    onChange={(e) => setSellerType(e.target.value)}
                    name="seller-types"
                >
                    <FormControlLabel value="all" control={<Radio />} label="הכל" />
                    <FormControlLabel value="private" control={<Radio />} label="פרטי" />
                    <FormControlLabel value="dealer" control={<Radio />} label="סוכנות" />
                </RadioGroup>
            </FormControl>
            {/* Owners */}
            <FormControl sx={{m: 3}} component="fieldset" variant="standard">
                <FormLabel component="legend">בעלים</FormLabel>
                <RadioGroup
                    value={ownerType}
                    onChange={(e) => setOwnerType(e.target.value)}
                    name="owner-types"
                >
                    <FormControlLabel value="all" control={<Radio />} label="הכל" />
                    <FormControlLabel value="private" control={<Radio />} label="פרטי" />
                    <FormControlLabel value="company" control={<Radio />} label="חברה" />
                    <FormControlLabel value="leasing" control={<Radio />} label="ליסינג" />
                </RadioGroup>
            </FormControl>
        </Box>
    );
}
