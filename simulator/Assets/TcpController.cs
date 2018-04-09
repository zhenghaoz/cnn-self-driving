using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;

public class TcpController : MonoBehaviour {

	public int controlPort;

	private CarController controller;

	public void Start() {
		controller = GetComponent<CarController> ();
		Thread serverThread = new Thread (new ThreadStart (TCPServer));
		serverThread.IsBackground = true;
		serverThread.Start ();
	}

	private void CommandEncode(byte[] data) {
		Debug.Assert (data.Length == 3);
		Debug.Log ("Control: recv " + BitConverter.ToString(data));
		if (data [0] == 0x00) {
			if (data [1] == 0x01) {
				Debug.Log ("Control: Forward");
				controller.Forward ();
			} else if (data [1] == 0x02) {
				Debug.Log ("Control: Backward");
				controller.Backward ();
			} else if (data [1] == 0x03) {
				Debug.Log ("Control: Turn Left");
				controller.TurnLeft ();
			} else if (data [1] == 0x04) {
				Debug.Log ("Control: Turn Right");
				controller.TurnRight ();
			} else if (data [1] == 0x00) {
				Debug.Log ("Control: Stop");
				controller.Stop ();
			}
		} else if (data[0] == 0x10) {
			Debug.Log ("Control: Reset");
			controller.Reset ();
		} else {
			Debug.Log ("Control: Invalid command");
		}
	}

	private void TCPServer() {
		IPEndPoint localEndPoint = new IPEndPoint(IPAddress.Any, controlPort);
		Socket listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
		listener.Bind(localEndPoint);
		listener.Listen(1);
		byte[] data = new byte[1];
		bool valid = false;
		List<byte> buffer = new List<byte>();
		while (true) {
			Debug.Log ("Control: Idle");
			Socket handler = listener.Accept ();
			Debug.Log ("Control: Connected");
			while (true) {
				int length = handler.Receive (data);
				if (length == 0)
					break;
				if (!valid) {
					// Parse header
					if (data [0] == 0xff) {
						buffer = new List<byte> ();
						valid = true;
					}
				} else {
					// Parse footer
					if (data [0] == 0xff) {
						valid = false;
						if (buffer.Count == 3)
							CommandEncode (buffer.ToArray ());
					} else {
						// Parse payload
						buffer.Add(data[0]);
					}
				}
			}
		}
	}
}
