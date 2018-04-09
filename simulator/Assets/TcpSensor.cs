using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;


public class TcpSensor : MonoBehaviour {

	public int sensorPort;

	private int reward;
	private CarController controller;
	private WebStream stream;

	public void Start() {
		controller = GetComponent<CarController> ();
		stream = GetComponent<WebStream> ();
		Thread serverThread = new Thread (new ThreadStart (TCPServer));
		serverThread.IsBackground = true;
		serverThread.Start ();
	}

	public void OnTriggerEnter(Collider other) {
		if (other.tag == "Disqualification") {
			controller.Out ();
		} else if (other.tag == "Milestone") {
			reward += 1;
		}
	}

	private void TCPServer() {
		IPEndPoint localEndPoint = new IPEndPoint(IPAddress.Any, sensorPort);
		Socket listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
		listener.Bind(localEndPoint);
		listener.Listen(1);
		byte[] data = new byte[1];
		while (true) {
			Debug.Log ("Sensor: Idle");
			Socket handler = listener.Accept ();
			Debug.Log ("Sensor: Connected");
			while (true) {
				int length = handler.Receive (data);
				if (length == 0)
					break;
				// Send sensor data
				handler.Send (BitConverter.GetBytes(controller.isOut()));
				// Send score data
				handler.Send(BitConverter.GetBytes(reward));
				reward = 0;
				// Send frame data
				handler.Send(BitConverter.GetBytes(stream.frame.Length));
				handler.Send (stream.frame);
			}
		}
	}
}
