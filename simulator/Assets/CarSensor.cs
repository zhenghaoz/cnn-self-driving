using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;


public class CarSensor : MonoBehaviour {

	public int sensorPort;

	private bool isOut = false;

	public void Start() {
		Thread serverThread = new Thread (new ThreadStart (TCPServer));
		serverThread.IsBackground = true;
		serverThread.Start ();
	}

	public void OnTriggerEnter(Collider other) {
		if (other.tag == "Disqualification") {
			isOut = true;
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
				// Response sensor data		
				data[0] = 0x00;
				if (isOut)
					data[0] = (byte)(data[0] | 0x01);
				handler.Send (data);
			}
		}
	}
}
