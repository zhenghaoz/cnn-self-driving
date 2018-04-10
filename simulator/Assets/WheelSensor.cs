using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class WheelSensor : MonoBehaviour {

	// Use this for initialization
	void Start () {
		
	}
	
	// Update is called once per frame
	void Update () {
		
	}


	public void OnTriggerEnter(Collider other) {
		if (other.tag == "Disqualification") {
			Debug.Log ("HW");
		} 
	}
}
