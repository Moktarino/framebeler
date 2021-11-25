from PIL import Image, ImageStat
import pickle, cv2, os, shutil, math, hashlib, json
from sortedcontainers import SortedDict


class Framebeler():
    current_video_num = 0
    videohash = None
    video_label_maps = None
    videopath = None
    videodir = None
    videos = None
    labels = None
    cap = None
    input_map = None
    fps = None
    framedelay = None

    colors = {
        'white': (255,255,255),
        'red': (0,0,255),
        'blue': (255,0,0),
        'black': (0,0,0),
        'grey': (225,225,225)
    }

    frameskip = 50
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = -1


    def write_json(self, filepath, data):
        with open(filepath, 'w') as outfile:
            json.dump(data, outfile)
            print(f"Written to: ./{filepath}")

    def read_json(self, filepath):
        if not os.path.exists(filepath):
            self.import_data(filepath, init=True)
        with open(filepath) as json_file:
            data = json.load(json_file)
        return data

    def import_data(self, datafile, init=False):

        def jsonKeys2int(x):
            if not x:
                return {}
            out_dict = SortedDict()
            for k1, v1 in x.items():
                tempdict = { k1: { int(k):v for k,v in x[k1].items() } }
                out_dict.update(**tempdict)
            return out_dict

        if init:
            print(f"Creating datafile: {datafile}")
            self.labels = [ 'test1', 'test2', 'test3' ]
            self.video_label_maps = {}
            self.save_data(datafile)
        else:
            data = self.read_json(datafile)
            self.labels = data['labels']
            self.video_label_maps = jsonKeys2int(data['label_maps'])

    def save_data(self, datafile):
        data = {
            'labels': self.labels,
            'label_maps': self.video_label_maps
        }
        self.write_json(datafile, data)

    def get_filehash(self, path):
        hasher = hashlib.md5()
        with open(path, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest().upper()

    def load_video(self):
        if not self.videos:
            self.videos = os.listdir(self.videodir)
        videopath = os.path.join(self.videodir, self.videos[self.current_video_num])
        print(f"{videopath}")
        self.videohash = self.get_filehash(videopath)
        if self.videohash not in self.video_label_maps.keys():
            self.video_label_maps[self.videohash] = SortedDict({0: []})
        
        self.cap = cv2.VideoCapture(videopath)

        if (self.cap.isOpened()== False):
            print(f"Error opening video file {self.current_video_num}: {videopath}")
            self.current_video_num += 1
            self.load_video()

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        print(f"FPS: {self.fps}")
        self.framedelay = int(1000 / self.fps)
        self.next_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.current_frame = self.next_frame - 1 if self.next_frame > 0 else 0
        self.previous_frame = self.current_frame - 1 if self.current_frame > 0 else 0



    def drawUI(self, frame, frame_id):
        self.input_map
        global video_label_maps
        shape = frame.shape
        image_height = shape[0]
        image_width = shape[1]
        rectangles = []
        selected_labels, _ = self.get_labels_for_frame(frame_id)

        for label in self.labels:
            color = self.colors['white']
            text_size, baseline = cv2.getTextSize(label, self.font, self.font_scale, self.thickness)
            text_width = text_size[0]
            text_height = text_size[1]
            rectangle = {
                'text_width': text_width,
                'text_height': text_height,
                'baseline': baseline,
                'text': label
            }
            rectangles.append(rectangle)
        
        y_bottom = 0
        for rectangle in rectangles:
            rectangle_color = self.colors['white']
            if rectangle['text'] in selected_labels:
                rectangle_color = self.colors['blue']
            textcolor = self.colors['black']
            x_offset = image_width - rectangle['text_width']
            y_top = y_bottom
            y_bottom += rectangle['text_height'] + rectangle['baseline']
            frame = cv2.rectangle(frame,(x_offset,y_top),(image_width,y_bottom), rectangle_color, self.thickness )
            frame = cv2.putText(frame, rectangle['text'], (x_offset, y_top + text_height), self.font, self.font_scale, textcolor, 2 )

            if rectangle['text'] not in [value for elem in self.input_map for value in elem.values()]:
                self.input_map.append({
                    'topleft_x': x_offset,
                    'topleft_y': y_top,
                    'bottomright_x': image_width,
                    'bottomright_y': y_bottom,
                    'label': rectangle['text']
                    }
                )
        return frame

    def draw_frame(self, frame, frame_id):
        frame = self.drawUI(frame, frame_id)
        cv2.namedWindow('Frame')
        cv2.setMouseCallback('Frame',self.get_input, (frame, frame_id))
        cv2.imshow('Frame',frame)

    def get_labels_for_frame(self, frame_id):
        is_inherited = False
        if frame_id not in self.video_label_maps[self.videohash].keys():
            all_maps = list(SortedDict(self.video_label_maps[self.videohash]).irange(0, frame_id))
            mapindex = -1 if len(all_maps) > 1 else 0
            last_labeled_frame_id = all_maps[mapindex]
            label_map = self.video_label_maps[self.videohash][last_labeled_frame_id].copy()
            is_inherited = True if mapindex != 0 else False
        else:
            label_map = self.video_label_maps[self.videohash][frame_id].copy()
        return label_map, is_inherited

    def update_label_maps(self, frame_id, current_labels):
        self.video_label_maps[self.videohash][int(frame_id)] = current_labels

    def get_input(self, event,x,y,flags,param):
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"Current Frame: {self.current_frame}")
            current_labels, is_inherited = self.get_labels_for_frame(self.current_frame)
            for input_box in self.input_map:
                label = input_box['label']
                frame = param[0]
                if (x >= input_box['topleft_x']) and ( y in range(input_box['topleft_y'], input_box['bottomright_y']+1)):
                    if label not in current_labels:
                        print(f"Adding label: {label} to frame ID: {self.current_frame}")
                        current_labels.append(label)
                    else:
                        print(f"Removing label: {label} frame ID: {self.current_frame}")
                        current_labels.remove(label)
                    self.update_label_maps(self.current_frame, current_labels) 
                    print("Current labels: ")
                    print(self.video_label_maps[self.videohash][self.current_frame])
                    self.draw_frame(frame, self.current_frame)

    def clear_labels(self):
        self.video_label_maps[self.videohash] = SortedDict({0:[]})

    def __init__(self, videodir, datafile='tag_data.json'):
        self.import_data(datafile)
        self.save_data(datafile)
        self.videodir = videodir
        self.input_map = []

        keys = {
            'up': 82,
            'down': 84,
            'left': 81,
            'right': 83,
            'esc': 27,
            'enter': 13,
            'n': 110,
            'p': 112,
            '[': 93,
            ']': 91,
            'c': 99
        }

        
        while True:
            self.load_video()
            while(self.cap.isOpened()):
                ret, frame = self.cap.read()
                if ret == True:
                    self.draw_frame(frame, self.current_frame)
                    key = cv2.waitKey(self.framedelay)
                    if not key == -1:
                        print(key)
                    if key in keys.values():
                        if key == keys['right']:  # Skip forward
                            self.current_frame += self.frameskip
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                        if key == keys['left']:  # Skip back
                            self.current_frame = (self.current_frame - self.frameskip) if self.current_frame >= self.frameskip else 0
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)          
                        if key == keys['c']:  # Clear all labels for current video
                            self.clear_labels()
                        if key == keys['[']:  # Speed up
                            self.framedelay = (self.framedelay - 10) if self.framedelay > 10 else 1 
                            print(self.framedelay) 
                        if key == keys[']']:  # Slow down
                            self.framedelay += 10
                            print(self.framedelay) 
                        if key == keys['n']:  # Next
                            self.current_video_num += 1
                            self.load_video()
                        if key == keys['p']:  # Previous
                            self.cap.release()
                            self.current_video_num = (self.current_video_num - 1) if not self.current_video_num == 0 else 0
                            self.load_video()
                        if key == keys['enter']:
                            self.save_data(datafile)
                        if key == keys['esc']:  # Quit
                            print("escape!")
                            cv2.destroyAllWindows()
                            self.save_data(datafile)
                            exit(0)
                    self.current_frame += 1        
                else:
                    break
            self.current_video_num += 1
        self.save_data(datafile)


fb = Framebeler(videodir='media', datafile="data.json")
