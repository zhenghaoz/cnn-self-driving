using UnityEngine;
using System.Collections.Generic;

public class CarController : MonoBehaviour {

	public float transportSpeed;
	public float rotateSpeed;

	private enum Action { Stop, Forward, Backward, TurnLeft, TurnRight }

	private Action action;
	private Stack<KeyCode> keyStack = new Stack<KeyCode>();
	private HashSet<KeyCode> keyPressed = new HashSet<KeyCode>();

	public void Start() {
		keyStack.Push (KeyCode.Space);
	}

	public void Update() {
		// Get input
		if (Input.GetKeyDown(KeyCode.W))
			KeyDown (KeyCode.W);
		if (Input.GetKeyDown(KeyCode.A))
			KeyDown (KeyCode.A);
		if (Input.GetKeyDown(KeyCode.S))
			KeyDown (KeyCode.S);
		if (Input.GetKeyDown(KeyCode.D))
			KeyDown (KeyCode.D);
		if (Input.GetKeyUp(KeyCode.W))
			KeyUp (KeyCode.W);
		if (Input.GetKeyUp(KeyCode.A))
			KeyUp (KeyCode.A);
		if (Input.GetKeyUp(KeyCode.S))
			KeyUp (KeyCode.S);
		if (Input.GetKeyUp(KeyCode.D))
			KeyUp (KeyCode.D);
		// Apply action
		switch(action) {
		case Action.Forward:
			transform.position += transform.forward * transportSpeed * Time.deltaTime;
			break;
		case Action.Backward:
			transform.position += transform.forward * -transportSpeed * Time.deltaTime;
			break;
		case Action.TurnLeft:
			transform.Rotate(Vector3.up * -rotateSpeed * Time.deltaTime, Space.World);
			break;
		case Action.TurnRight:
			transform.Rotate(Vector3.up * rotateSpeed * Time.deltaTime, Space.World);
			break;
		}
	}

	private void KeyDown(KeyCode keyCode) {
		if (!keyPressed.Contains (keyCode)) 
			KeyApply (keyCode);
			keyPressed.Add (keyCode);
			keyStack.Push (keyCode);
	}

	private void KeyUp(KeyCode keyCode) {
		if (keyPressed.Contains (keyCode))
			keyPressed.Remove (keyCode);
		while (keyStack.Count > 1) {
			if (!keyPressed.Contains (keyStack.Peek ()))
				keyStack.Pop ();
			else
				break;
		}
		KeyApply (keyStack.Peek ());
	}

	private void KeyApply(KeyCode keyCode) {
		switch (keyCode) {
		case KeyCode.Space:
			Stop ();
			break;
		case KeyCode.W:
			Forward ();
			break;
		case KeyCode.S:
			Backward ();
			break;
		case KeyCode.A:
			TurnLeft ();
			break;
		case KeyCode.D:
			TurnRight ();
			break;
		}
	}
		
	public void Stop() {
		action = Action.Stop;
	}

	public void Forward() {
		action = Action.Forward;
	}

	public void Backward() {
		action = Action.Backward;
	}

	public void TurnLeft() {
		action = Action.TurnLeft;
	}

	public void TurnRight() {
		action = Action.TurnRight;
	}
}
