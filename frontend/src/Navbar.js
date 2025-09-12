import React from 'react';
import {Link} from "react-router-dom";
import './Navbar.css';
import {Home, ShowChart, Task} from "@mui/icons-material";
import {BottomNavigation, BottomNavigationAction} from "@mui/material";
import Box from "@mui/material/Box";

// function Navbar() {
//     return (
//         <div className='navigation-menu'>
//             <ol>
//                 <li><Link to={"/Tasks"}>Tasks</Link></li>
//                 <li><Link to={"/"}>Home</Link></li>
//             </ol>
//         </div>
//
// )
// }

function Navbar() {
    const [value, setValue] = React.useState('signal');
    return (
        <Box sx={{ width: 500 }}>
            <BottomNavigation showLabels value={value} onChange={(event, newValue) => {
                setValue(newValue);
            }}>
                <BottomNavigationAction
                    component={Link}
                    to="/tasks"
                    label="Tasks"
                    value="tasks"
                    icon={<Task />}
                    // className={classes.content}
                />
                <BottomNavigationAction
                    component={Link}
                    to="/"
                    label="Home"
                    value="home"
                    icon={<Home />}
                    // className={classes.content}
                />
            </BottomNavigation>
        </Box>

)
}

export default Navbar
