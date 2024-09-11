import axios from 'axios';

// Function to add a task
export async function addTask(
  username: string,
  task_description: string,
  tasks: any,
  setTasks: any
) {
  let taskInfo = {
    task_name: task_description,
    task_status: 'pending',
  };

  try {
    // Fetch data from the API using Axios
    const url = `http://0.0.0.0:8080/ping/`;
    const response = await axios.get<{ result: string }>(url);
    const result = response.data.result;

    if (result === 'pong') {
      console.log("pong received successfully");

      // Open a WebSocket connection
      createWebSocketConnection(username);

      return taskInfo;
    } else if (result === 'fail') {
      console.log("Task add failed");
      return 'failed';
    } else if (result === 'task_already_exists') {
      console.log("Task already exists");
      return 'exists';
    } else {
      console.log("Task add failed");
      console.log(result);
      return 'task_add failed';
    }
  } catch (error) {
    console.error('Error fetching data:', error);
  }
}

// Function to create a WebSocket connection
function createWebSocketConnection(username: string) {
  // Replace the URL with your WebSocket endpoint
  const socket = new WebSocket('ws://0.0.0.0:8080/ws/some_path/');

  // Open event: When the connection is established
  socket.onopen = function() {
    console.log('WebSocket connection established');

    // Send a message to the server via WebSocket
    socket.send(JSON.stringify({
      'message': `User ${username} connected via WebSocket`
    }));
  };

  // Message event: When a message is received from the server
  socket.onmessage = function(event) {
    console.log('Message from server: ', event.data);
  };

  // Close event: When the WebSocket connection is closed
  socket.onclose = function() {
    console.log('WebSocket connection closed');
  };

  // Error event: When an error occurs with the WebSocket connection
  socket.onerror = function(error) {
    console.error('WebSocket error: ', error);
  };
}

// Call the addTask function
// addTask('test_user', 'test_task', [], (newTasks: any) => {
//   console.log('Updated tasks:', newTasks);
// });

const username = 'test_user';
createWebSocketConnection(username);
