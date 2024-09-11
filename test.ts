import axios from 'axios';
import path from 'path';
import os from 'os';
import fs from 'fs';
import WebSocket from 'ws';


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
    const url = `http://website2-389236221119.us-central1.run.app/ping/`;
    const response = await axios.get<{ result: string }>(url);
    const result = response.data.result;

    if (result === 'pong') {
      console.log("pong received successfully");

      // Open a WebSocket connection
      createWebSocketConnection(username, device_name);

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
function createWebSocketConnection(username: string, device_name: string) {
  // Replace the URL with your WebSocket endpoint
  const socket = new WebSocket('ws://0.0.0.0:8080/ws/live_data/');
  // const socket = new WebSocket('wss://website2-389236221119.us-central1.run.app/ws/live_data/');

  // Open event: When the connection is established
  socket.onopen = function() {
    console.log('WebSocket connection established');

    const message = {
      'message': `Initiate live data connection`,
      'username': username,
      'device_name': device_name
    };
    socket.send(JSON.stringify(message));
    console.log(`Sent: ${JSON.stringify(message)}`);

    // Message event: When a message is received from the server
    socket.onmessage = function(event: any) {
      console.log('Message from server: ', event.data);

      // Split the message into separate variables
      const data = JSON.parse(event.data);
      const message = data.message;
      const request_type = data.request_type;
      const file_name = data.file_name;

      if (request_type === 'file_request') {
        console.log(`Received download request for file: ${file_name}`);
        // Search for the file in the local directory
        console.log(`Searching for file: ${file_name}`);
        const directory_name: string = "BCloud";
        const directory_path: string = path.join(os.homedir(), directory_name);
        const file_save_path: string = path.join(directory_path, file_name);
        let request_file_name = path.basename(file_save_path);
        // If the file exists, send the file to the server
        const file: fs.ReadStream = fs.createReadStream(file_save_path);
        file.on('open', () => {
          console.log(`Sending file: ${request_file_name}`);
          // Send the file to the server
        });
        // If the file does not exist, send a message to the server
        file.on('error', (err: any) => {
          console.log(`File not found: ${request_file_name}`);
          const message = {
            'message': `File not found`,
            'username': username,
            'device_name': device_name,
            'file_name': request_file_name
          };
          socket.send(JSON.stringify(message));
          console.log(`Sent: ${JSON.stringify(message)}`);
        });
      }
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
}

function download_request(username: string, file_name: string) {
  // Replace the URL with your WebSocket endpoint
  const socket = new WebSocket('ws://0.0.0.0:8080/ws/download_request/');
  // const socket = new WebSocket('wss://website2-389236221119.us-central1.run.app/ws/download_request/');

  // Message event: When a message is received from the server
  socket.onmessage = function(event) {
    console.log('Message from server: ', event.data);
  };

  // Open event: When the connection is established
  socket.onopen = function() {
    console.log('WebSocket connection established');

    // Send a download request message to the server
    const message = {
      'message': `Download Request`,
      'username': username,
      'file_name': file_name
    };
    socket.send(JSON.stringify(message));
    console.log(`Sent: ${JSON.stringify(message)}`);
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
// console.log('Updated tasks:', newTasks);
// });

const username = 'mmills';
const file_name = 'Logo.png';
const device_name = 'michael-ubuntu';
createWebSocketConnection(username, device_name);
download_request(username, file_name);

