def update_known_face_information(new_encoding, new_metadata):
    update_known_faces_encodings(new_encoding)
    update_known_faces_metadata(new_metadata)


def update_known_faces_metadata(new_metadata):
    global known_face_metadata
    known_face_metadata.append(new_metadata)


def display_recent_visitors_face(known_face_metadata, frame):
    number_of_recent_visitors = 0
    for metadata in known_face_metadata:
        # If we have seen this person in the last minute, draw their image
        if datetime.now() - metadata["last_seen"] < timedelta(seconds=10) and metadata["seen_frames"] > 1:
            # Draw the known face image
            x_position = number_of_recent_visitors * 150
            frame[30:180, x_position:x_position + 150] = metadata["face_image"]
            number_of_recent_visitors += 1

            # Label the image with how many times they have visited
            visits = metadata['seen_count']
            visit_label = f"{visits} visits"
            if visits == 1:
                visit_label = "First visit"
            cv2.putText(frame, visit_label, (x_position + 10, 170), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)


