using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;


public class DirectController : MonoBehaviour {

	public int direcPort;
	public int directWidth;
	public int directHeight;
	public float deltaTime;
	public Camera frontCamera;
	public List<GameObject> distanceSensors;

	private bool updated = false;
	private Socket handler;
	private CarController controller;
	private RenderTexture rt;
	private ManualResetEvent evt = new ManualResetEvent(true);

	public void Start() {
		rt = new RenderTexture(directWidth, directHeight, 24);
		controller = GetComponent<CarController> ();
		Thread serverThread = new Thread (new ThreadStart (TCPServer));
		serverThread.IsBackground = true;
		serverThread.Start ();
	}

	public void Update() {
		if (handler == null)
			return;
		bool disconnected = false;
		string message = "Disconnected";
		try {
			byte[] data = new byte[1];
			int length = handler.Receive(data);
			if (length < 1)
				disconnected = true;
			Debug.Log ("Direct: recv " + BitConverter.ToString(data));
			switch (data[0]) {
			case 0x00:
				controller.RotateLeft(deltaTime);
				break;
			case 0x01:
				controller.RotateRight(deltaTime);
				break;
			case 0x02:
				controller.MoveForward(deltaTime);
				break;
			case 0xff:
				controller.Reset();
				break;
			}
			updated = true;
		} catch (Exception e) {
			disconnected = true;
			message = e.Message;
		}
		// Reset handler after disconnected
		if (disconnected) {
			Debug.Log ("Direct: " + message);
			handler = null;
			evt.Set ();
		}
	}

	public void LateUpdate() {
		if (!updated)
			return;
		updated = false;
		try {
			// Send isOut
			handler.Send(BitConverter.GetBytes(controller.isOut()));
			// Render frame
			frontCamera.targetTexture = rt;
			Texture2D screenShot = new Texture2D(directWidth, directHeight, TextureFormat.RGB24, false);
			frontCamera.Render();
			RenderTexture.active = rt;
			screenShot.ReadPixels(new Rect(0, 0, directWidth, directHeight), 0, 0);
			frontCamera.targetTexture = null;
			RenderTexture.active = null;
			byte[] frame = screenShot.EncodeToJPG ();
			Destroy (screenShot);
			// Send frame
			handler.Send(BitConverter.GetBytes(frame.Length));
			handler.Send(frame);
			// Detect distance
			float[] distance = new float[distanceSensors.Count];
			for (int i = 0; i < distance.Length; i++) {
				GameObject sensor = distanceSensors[i];
				RaycastHit hit;
				if (Physics.Raycast (sensor.transform.position, sensor.transform.TransformDirection (Vector3.forward), out hit))
					distance[i] = hit.distance;
				else
					distance[i] = float.NaN;
			}
			// Send distance
			handler.Send(BitConverter.GetBytes(distance.Length));
			for (int i = 0; i < distance.Length; i++)
				handler.Send(BitConverter.GetBytes(distance[i]));
		} catch (Exception e) {
			Debug.Log ("Direct: " + e.Message);
			handler = null;
			evt.Set ();
		}
	}

	private void TCPServer() {
		IPEndPoint localEndPoint = new IPEndPoint(IPAddress.Any, direcPort);
		Socket listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
		listener.Bind(localEndPoint);
		listener.Listen(1);
		byte[] data = new byte[1];
		while (true) {
			evt.WaitOne ();
			Debug.Log ("Direct: Idle");
			handler = listener.Accept ();
			Debug.Log ("Direct: Connected");
		}
	}
}