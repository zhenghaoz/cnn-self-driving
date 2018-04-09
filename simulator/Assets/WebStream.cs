using UnityEngine;
using System;
using System.Text; 
using System.Net;
using System.Net.Sockets;
using System.Threading;

public class WebStream : MonoBehaviour
{
	public int streamFPS;
	public int streamWidth;
	public int streamHeight;
	public int streamPort;
	public Camera streamCamera;
	public byte[] frame;

	private Socket handler;
	private Socket listener;
	private RenderTexture rt;
	private Texture2D screenShot;

	public void Start() {
		Application.targetFrameRate = streamFPS; 
		rt = new RenderTexture(streamWidth, streamHeight, 24);
		// Setup HTTP server
		IPEndPoint localEndPoint = new IPEndPoint(IPAddress.Any, streamPort);
		listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
		listener.Bind(localEndPoint);
		listener.Listen(1);
		// Setup accept thread
		Thread acceptThread = new Thread (new ThreadStart(HTTPConnectionHandler));
		acceptThread.IsBackground = true;
		acceptThread.Start ();
	}

	public void LateUpdate() {
		// Render frame
		streamCamera.targetTexture = rt;
		Destroy (screenShot);
		screenShot = new Texture2D(streamWidth, streamHeight, TextureFormat.RGB24, false);
		streamCamera.Render();
		RenderTexture.active = rt;
		screenShot.ReadPixels(new Rect(0, 0, streamWidth, streamHeight), 0, 0);
		streamCamera.targetTexture = null;
		RenderTexture.active = null;
		// Encode frame data
		frame = screenShot.EncodeToJPG();
		if (handler != null) {
			// Encode frame header
			string header = "--b\r\n"
				+ "Content-Type: image/jpeg\r\n"
				+ "Content-length: " + frame.Length.ToString() + "\r\n" 
				+ "\r\n";
			byte[] bytes = Encoding.UTF8.GetBytes(header);
			// Send data
			try {
				handler.Send (bytes);
				handler.Send (frame);
			} catch (Exception e) {
				Debug.Log("Stream: Disconnected");
				handler = null;
				// Restart HTTP handler
				Thread acceptThread = new Thread (new ThreadStart(HTTPConnectionHandler));
				acceptThread.IsBackground = true;
				acceptThread.Start ();
			}
		}
	}

	private void HTTPConnectionHandler() {
		// Accept HTTP connection
		Debug.Log ("Stream: Idle");
		handler = listener.Accept ();
		Debug.Log ("Stream: Connected");
		while (true) {
			byte[] bytes = new Byte[1024];  
			int bytesRec = handler.Receive (bytes);  
			string data = Encoding.ASCII.GetString (bytes, 0, bytesRec);  
			if (data.IndexOf ("\r\n\r\n") != -1)
				break;
		}
		// Send HTTP header
		string header = "HTTP/1.1 200 OK\r\n"
		                + "Content-Type: multipart/x-mixed-replace; boundary=b\r\n"
		                + "\r\n";
		byte[] headerData = System.Text.Encoding.UTF8.GetBytes (header);
		handler.Send (headerData);
	}
}
