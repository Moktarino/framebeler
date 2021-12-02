from PIL import Image, ImageStat
import pickle, cv2, os, shutil, math, hashlib, json, time, pygame
from sortedcontainers import SortedDict


class Framebeler():
    pygame.init()
    clock = pygame.time.Clock()
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
    frame = None
    paused = False
    update_after_input = False
    vc = None
    
    colors = {
        'white': (255,255,255),
        'red': (0,0,255),
        'blue': (255,0,0),
        'black': (0,0,0),
        'grey': (225,225,225)
    }

    speed_adjust_increment = 10
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
        if self.fps < 1:
            self.fps == 30
            print("Video missing FPS property, setting to a default of 30")
        print(f"FPS: {self.fps}")
        self.next_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.current_frame = self.next_frame - 1 if self.next_frame > 0 else 0
        self.previous_frame = self.current_frame - 1 if self.current_frame > 0 else 0


    def drawUI(self):
        image_height = self.frame.shape[0]
        image_width = self.frame.shape[1]
        rectangles = []
        selected_labels, _ = self.get_labels_for_frame(self.current_frame)

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
            self.frame = cv2.rectangle(self.frame,(x_offset,y_top),(image_width,y_bottom), rectangle_color, self.thickness )
            self.frame = cv2.putText(self.frame, rectangle['text'], (x_offset, y_top + text_height), self.font, self.font_scale, textcolor, 2 )

            if rectangle['text'] not in [value for elem in self.input_map for value in elem.values()]:
                self.input_map.append({
                    'topleft_x': x_offset,
                    'topleft_y': y_top,
                    'bottomright_x': image_width,
                    'bottomright_y': y_bottom,
                    'label': rectangle['text']
                    }
                )
        #return frame


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


    def clear_labels(self, vc):
        self.video_label_maps[self.videohash] = SortedDict({0:[]})
        vc.draw_frame()



        
    class VideoController():
        parent = None
        video_end = False
        screen = None


        def __init__(self, parent):
            self.parent = parent
        

        def load_video(self):
            if not self.parent.videos:
                self.parent.videos = os.listdir(self.parent.videodir)
            if self.parent.current_video_num >= len(self.parent.videos):
                self.parent.current_video_num = 0
            videopath = os.path.join(self.parent.videodir, self.parent.videos[self.parent.current_video_num])
            print(f"{videopath}")
            self.parent.videohash = self.parent.get_filehash(videopath)
            if self.parent.videohash not in self.parent.video_label_maps.keys():
                self.parent.video_label_maps[self.parent.videohash] = SortedDict({0: []})
            
            self.parent.cap = cv2.VideoCapture(videopath)
            self.video_end = False

            if (self.parent.cap.isOpened()== False):
                print(f"Error opening video file {self.parent.current_video_num}: {videopath}")
                self.parent.current_video_num += 1
                self.parent.load_video()

            self.parent.fps = self.parent.cap.get(cv2.CAP_PROP_FPS)
            print(f"FPS: {self.parent.fps}")

            self.parent.next_frame = int(self.parent.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.parent.current_frame = self.parent.next_frame - 1 if self.parent.next_frame > 0 else 0
            self.parent.previous_frame = self.parent.current_frame - 1 if self.parent.current_frame > 0 else 0
            

        def draw_frame(self):
            self.parent.drawUI()
            image = pygame.image.frombuffer(self.parent.frame.tostring(), self.parent.frame.shape[1::-1], "RGB")
            if not self.screen:
                self.screen = pygame.display.set_mode((image.get_width(),image.get_height()))
            self.screen.blit(image, (0,0))
            pygame.display.update()
            self.parent.clock.tick(self.parent.fps)


        def skip_frames(self, direction):
            print("Skipping forward")
            if direction == "forward":
                self.parent.current_frame += self.parent.frameskip
            if direction == "back":
                self.parent.current_frame = (self.parent.current_frame - self.parent.frameskip) if self.parent.current_frame >= self.parent.frameskip else 0
            
            self.show_frame()


        def show_frame(self):
            video_pos = int(self.parent.cap.get(cv2.CAP_PROP_POS_FRAMES))

            read_new_frame = True
            if self.parent.paused:
                read_new_frame = False

            if abs(self.parent.current_frame - video_pos) > 1:
                self.parent.cap.set(cv2.CAP_PROP_POS_FRAMES, self.parent.current_frame - 1)
                read_new_frame = True

            if read_new_frame:
                ret, self.parent.frame = self.parent.cap.read()
                self.parent.current_frame = int(self.parent.cap.get(cv2.CAP_PROP_POS_FRAMES))
                if ret == True:
                    self.draw_frame()
                else:
                    self.parent.cap.release()  
                    self.video_end = True 


    def process_mouse_input(self, event, vc):
        print(f"Current Frame: {self.current_frame}")
        current_labels, _ = self.get_labels_for_frame(self.current_frame)
        x, y = event.pos
        for input_box in self.input_map:
            label = input_box['label']
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
                vc.draw_frame()


    def process_keyboard_input(self, event, vc):
        if event.key == pygame.K_LEFTBRACKET:
            self.fps -= 1
        if event.key == pygame.K_RIGHTBRACKET:
            self.fps += 1
        if event.key == pygame.K_RIGHT:
            vc.skip_frames("forward")            
        if event.key == pygame.K_LEFT:
            vc.skip_frames("back")  
        if event.key == pygame.K_c:
            self.clear_labels(vc)
        if event.key == pygame.K_n:
            self.current_video_num += 1
            vc.load_video()
        if event.key == pygame.K_p:
            self.current_video_num = (self.current_video_num - 1) if not self.current_video_num == 0 else 0
            vc.load_video()
        if event.key == pygame.K_SPACE:
            self.paused = False if self.paused == True else True
        if event.key == pygame.K_RETURN:
            self.save_data(datafile)
        if event.key == pygame.K_ESCAPE:
            cv2.destroyAllWindows()
            self.save_data(self.datafile)
            exit(0)


    def get_input(self, vc):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.process_mouse_input(event, vc)
            if event.type == pygame.KEYDOWN:
                self.process_keyboard_input(event, vc)


    def __init__(self, videodir, datafile='tag_data.json'):
        self.datafile = datafile
        self.import_data(datafile)
        self.save_data(datafile)
        self.videodir = videodir
        self.input_map = []
        self.vc = self.VideoController(self)
    

    def begin(self):
        while True:
            self.vc.load_video()
            while(not self.vc.video_end):
                self.vc.show_frame()
                self.get_input(self.vc)
            self.current_video_num += 1
        self.save_data(self.datafile)



if __name__ = "__main__":
    fb = Framebeler(videodir='media', datafile="data.json")
    fb.begin()
