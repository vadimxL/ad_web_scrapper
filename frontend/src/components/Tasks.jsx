import {useEffect, useState} from "react";
import {Accordion, AccordionDetails, AccordionSummary} from "@mui/material";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Navbar from "../Navbar";
import Container from "@mui/material/Container";
import {createTheme, ThemeProvider} from "@mui/material/styles";
import * as PropTypes from "prop-types";


function ArrowDownwardIcon() {
    return null;
}

function DeleteTask({id}) {
    const deleteTodo = async () => {
        await fetch(`http://localhost:8000/tasks/${id}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: { "id": id }
        })
        await fetchTasks()
    }

    return (
        <Button h="1.5rem" size="sm" onClick={deleteTodo}>Delete Todo</Button>
    )
}

function Price(params) {
    if ("price" in params) {
        return (
            <div>
                <Typography color="primary" level="title-lg">Price Range:</Typography>
                <Typography level="body-lg"> {params.price} </Typography>
            </div>
        )
    }
    return null;
}

function Task(props) {
    return <Accordion>
        <AccordionSummary
            expandIcon={<ArrowDownwardIcon/>}
            aria-controls="panel1-content"
            id="panel1-header"
        >
            <Typography>{"id: " + props.task.id}</Typography>
        </AccordionSummary>
        <AccordionDetails>
            {/*{task.car_models.map((model) => (*/}
            {/*    <Typography key={model} color="primary" variant="body2">*/}
            {/*        {model}*/}
            {/*    </Typography>*/}
            {/*))}*/}
            <Typography color="primary" level="title-lg">Manufacturers:</Typography>
            <Typography level="body-lg"> {props.task.manufacturers} </Typography>
            <Typography color="primary" level="title-lg">Models:</Typography>
            <Typography level="body-lg"> {props.task.car_models} </Typography>
            <Typography color="primary" level="title-lg">Submodels:</Typography>
            <Typography level="body-lg"> {props.task.car_submodels} </Typography>
            <Price params={props.task.params}/>
            <DeleteTask id={props.task.id}/>
        </AccordionDetails>
    </Accordion>;
}

Task.propTypes = {task: PropTypes.any};
export default function Tasks() {
    const [tasks, setTasks] = useState([]);

    const fetchTasks = () => {
        fetch("http://localhost:8000/tasks")
            .then((r) => r.json())
            .then((tasks) => setTasks(tasks));
    }

    console.log("Fetching tasks...." + tasks);
    useEffect(() => {
        fetchTasks();
    }, []);

    const defaultTheme = createTheme();

    return (
        <div>
            <ThemeProvider theme={defaultTheme}>
            <Container component="main" maxWidth="xs">
            <Navbar />
            {tasks.map((task) => {
                return (<Task task={task}/>)
            })}
            </Container>
            </ThemeProvider>
        </div>
    )
}