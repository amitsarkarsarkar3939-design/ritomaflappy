import javax.swing.BorderFactory;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingUtilities;
import javax.swing.Timer;
import java.awt.BasicStroke;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.GradientPaint;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.awt.geom.Ellipse2D;
import java.awt.geom.RoundRectangle2D;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class idk {
    private static final String API = "http://127.0.0.1:8765";
    private static final ExecutorService NETWORK = Executors.newSingleThreadExecutor();
    private static Process apiProcess;
    private static final Map<String, Color[]> SKINS = new LinkedHashMap<String, Color[]>();

    static {
        SKINS.put("Sunny", colors("#87dff2", "#8bd5a5", "#55ae76", "#45b96c", "#ffd34d", "#ffc83d"));
        SKINS.put("Sunset", colors("#fa967e", "#c77f8b", "#875578", "#d76e59", "#ffda73", "#ffe16b"));
        SKINS.put("Midnight", colors("#1b2b58", "#4c648b", "#263b68", "#399d9b", "#b9e5ff", "#ffe178"));
        SKINS.put("Spooky", colors("#171829", "#39304e", "#201e38", "#7762a6", "#d4c2ff", "#b8f17d"));
        SKINS.put("Party", colors("#ffb5d5", "#a7e4c4", "#65bd9b", "#ed79b7", "#fff07c", "#ffe34a"));
    }

    private static Color[] colors(String... values) {
        Color[] result = new Color[values.length];
        for (int i = 0; i < values.length; i++) result[i] = Color.decode(values[i]);
        return result;
    }

    public static void main(String[] args) {
        try {
            ensureService();
        } catch (Exception error) {
            JOptionPane.showMessageDialog(null,
                    "Could not start the local game service.\n" + error.getMessage()
                            + "\nInstall Python 3, then run this app from the project folder.",
                    "Flappy Friends", JOptionPane.ERROR_MESSAGE);
            return;
        }
        SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                new GameWindow().setVisible(true);
            }
        });
    }

    private static void ensureService() throws Exception {
        if (serviceIsReady()) return;
        Path script = Paths.get("game.py").toAbsolutePath();
        if (!Files.isRegularFile(script)) {
            throw new IllegalStateException("game.py was not found. Run the Java app from the project folder.");
        }
        File folder = script.getParent().toFile();
        apiProcess = new ProcessBuilder("python", script.toString(), "--server-only")
                .directory(folder).redirectErrorStream(true).start();
        long deadline = System.currentTimeMillis() + 10000;
        while (System.currentTimeMillis() < deadline) {
            if (serviceIsReady()) return;
            if (!apiProcess.isAlive()) throw new IllegalStateException("Python service exited. Check Python is installed.");
            Thread.sleep(250);
        }
        apiProcess.destroy();
        throw new IllegalStateException("Python service did not respond on port 8765.");
    }

    private static boolean serviceIsReady() {
        try {
            request("GET", "/api/health", null);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    private static String request(String method, String path, String body) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(API + path).openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(2500);
        connection.setReadTimeout(path.startsWith("/api/purchase") ? 45000 : 6000);
        if (body != null) {
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] data = body.getBytes(StandardCharsets.UTF_8);
            connection.getOutputStream().write(data);
        }
        int status = connection.getResponseCode();
        InputStream input = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int count;
        while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
        input.close();
        connection.disconnect();
        String text = new String(output.toByteArray(), StandardCharsets.UTF_8);
        if (status >= 400) {
            Object parsed = new JsonParser(text).parse();
            Object error = ((Map<?, ?>) parsed).get("error");
            throw new IllegalStateException(error == null ? "Service request failed (" + status + ")." : error.toString());
        }
        return text;
    }

    private static Map<String, Object> object(Object value) {
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) value;
        return result;
    }

    private static List<Object> array(Object value) {
        @SuppressWarnings("unchecked")
        List<Object> result = (List<Object>) value;
        return result;
    }

    private static String jsonString(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private static final class Mode {
        final String id;
        final String label;
        final String description;
        final double gravity;
        final double flap;
        final int gap;
        final double speed;
        final double interval;

        Mode(Map<String, Object> row) {
            id = (String) row.get("mode_id");
            label = (String) row.get("display_name");
            description = (String) row.get("description");
            gravity = number(row.get("gravity"));
            flap = number(row.get("flap_strength"));
            gap = (int) number(row.get("pipe_gap"));
            speed = number(row.get("pipe_speed"));
            interval = number(row.get("spawn_interval"));
        }

        public String toString() { return label; }
    }

    private static double number(Object value) {
        return ((Number) value).doubleValue();
    }

    private static final class GameWindow extends JFrame {
        private final Map<String, Mode> modes = new LinkedHashMap<String, Mode>();
        private final JComboBox<Mode> modePicker = new JComboBox<Mode>();
        private final JComboBox<String> skinPicker = new JComboBox<String>(SKINS.keySet().toArray(new String[0]));
        private final JLabel stats = new JLabel("Score 0     Coins 0     Wallet 0     Best 0");
        private final JLabel status = new JLabel("Loading game...");
        private final GamePanel game = new GamePanel();
        private final Timer purchaseTimer;
        private String orderId;
        private int balance;
        private int best;
        private boolean closing;
        private boolean checkingPurchase;

        GameWindow() {
            super("Flappy Friends - Desktop");
            setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
            setMinimumSize(new Dimension(480, 520));
            setSize(600, 760);
            setLocationRelativeTo(null);

            JPanel root = new JPanel(new BorderLayout(8, 8));
            root.setBackground(new Color(242, 248, 255));
            root.setBorder(BorderFactory.createEmptyBorder(12, 14, 12, 14));
            JLabel title = new JLabel("FLAPPY FRIENDS", JLabel.CENTER);
            title.setFont(new Font("SansSerif", Font.BOLD, 25));
            JLabel subtitle = new JLabel("Choose a mode, collect coins, and fly with your friends.", JLabel.CENTER);
            JPanel heading = new JPanel(new BorderLayout(3, 3));
            heading.setOpaque(false);
            heading.add(title, BorderLayout.NORTH);
            heading.add(subtitle, BorderLayout.SOUTH);
            root.add(heading, BorderLayout.NORTH);

            JPanel center = new JPanel(new BorderLayout(5, 5));
            center.setOpaque(false);
            stats.setHorizontalAlignment(JLabel.CENTER);
            stats.setFont(new Font("SansSerif", Font.BOLD, 15));
            center.add(stats, BorderLayout.NORTH);
            game.setPreferredSize(new Dimension(480, 640));
            center.add(game, BorderLayout.CENTER);

            JPanel controls = new JPanel();
            controls.setOpaque(false);
            controls.add(new JLabel("Mode"));
            controls.add(modePicker);
            controls.add(new JLabel("Skin"));
            controls.add(skinPicker);
            center.add(controls, BorderLayout.SOUTH);
            root.add(center, BorderLayout.CENTER);
            root.add(buildShop(), BorderLayout.SOUTH);
            JScrollPane scrollPane = new JScrollPane(root);
            scrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
            scrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
            scrollPane.getVerticalScrollBar().setUnitIncrement(28);
            setContentPane(scrollPane);

            loadModes();
            modePicker.addActionListener(event -> {
                Mode selected = (Mode) modePicker.getSelectedItem();
                if (selected != null) {
                    game.setMode(selected);
                    loadProfile(selected.id);
                    status.setText(selected.description);
                }
            });
            skinPicker.addActionListener(event -> game.setSkin((String) skinPicker.getSelectedItem()));
            purchaseTimer = new Timer(2500, event -> pollPurchase());
            purchaseTimer.setRepeats(true);
            addWindowListener(new WindowAdapter() {
                public void windowClosed(WindowEvent event) {
                    closing = true;
                    purchaseTimer.stop();
                    NETWORK.shutdownNow();
                    if (apiProcess != null) apiProcess.destroy();
                }
            });
            game.setOnStats(() -> {
                stats.setText("Score " + game.score + "     Run coins " + game.runCoins
                        + "     Wallet " + balance + "     Best " + best);
            });
        }

        private JPanel buildShop() {
            JPanel shop = new JPanel();
            shop.setLayout(new BoxLayout(shop, BoxLayout.Y_AXIS));
            shop.setOpaque(false);
            shop.setBorder(BorderFactory.createTitledBorder("Coin shop"));
            String[][] packs = {
                    {"mini", "10 coins · ₹2"},
                    {"starter", "100 coins · ₹10"},
                    {"double", "200 coins · ₹20"},
                    {"happy", "350 coins · ₹25"},
                    {"mega", "1000 coins · ₹100"},
                    {"super", "2000 coins · ₹90"}
            };
            for (int row = 0; row < 2; row++) {
                JPanel line = new JPanel(new BorderLayout(4, 4));
                line.setOpaque(false);
                for (int col = 0; col < 3; col++) {
                    String[] pack = packs[row * 3 + col];
                    JButton button = new JButton(pack[1]);
                    button.addActionListener(event -> createPurchase(pack[0]));
                    line.add(button, col == 0 ? BorderLayout.WEST : col == 1 ? BorderLayout.CENTER : BorderLayout.EAST);
                }
                shop.add(line);
            }
            status.setFont(new Font("SansSerif", Font.PLAIN, 12));
            shop.add(status);
            JLabel note = new JLabel("Razorpay checkout · coins unlock after server confirmation.");
            note.setFont(new Font("SansSerif", Font.PLAIN, 11));
            shop.add(note);
            return shop;
        }

        private void loadModes() {
            NETWORK.execute(() -> {
                try {
                    Map<String, Object> response = object(new JsonParser(request("GET", "/api/modes", null)).parse());
                    List<Object> rows = array(response.get("modes"));
                    SwingUtilities.invokeLater(() -> {
                        for (Object row : rows) {
                            Mode mode = new Mode(object(row));
                            modes.put(mode.id, mode);
                            modePicker.addItem(mode);
                        }
                        for (int i = 0; i < modePicker.getItemCount(); i++) {
                            if ("classic".equals(modePicker.getItemAt(i).id)) modePicker.setSelectedIndex(i);
                        }
                    });
                } catch (Exception error) {
                    SwingUtilities.invokeLater(() -> status.setText("Could not load game modes: " + error.getMessage()));
                }
            });
        }

        private void loadProfile(String mode) {
            NETWORK.execute(() -> {
                try {
                    String encoded = URLEncoder.encode(mode, "UTF-8");
                    Map<String, Object> result = object(new JsonParser(
                            request("GET", "/api/profile?mode=" + encoded, null)).parse());
                    balance = ((Number) result.get("balance")).intValue();
                    best = ((Number) result.get("best")).intValue();
                    SwingUtilities.invokeLater(() -> game.repaint());
                } catch (Exception error) {
                    SwingUtilities.invokeLater(() -> status.setText("Could not load scores: " + error.getMessage()));
                }
            });
        }

        private void createPurchase(String packId) {
            status.setText("Connecting to Razorpay...");
            NETWORK.execute(() -> {
                try {
                    String result = request("POST", "/api/purchase",
                            "{\"pack_id\":" + jsonString(packId) + "}");
                    Map<String, Object> order = object(new JsonParser(result).parse());
                    String id = (String) order.get("merchant_order_id");
                    String checkout = (String) order.get("checkout_url");
                    SwingUtilities.invokeLater(() -> {
                        if (closing) return;
                        orderId = id;
                        status.setText("Secure checkout opened. Waiting for Razorpay confirmation...");
                        try {
                            if (!Desktop.isDesktopSupported()) throw new IllegalStateException("A web browser could not be opened.");
                            Desktop.getDesktop().browse(new URI(checkout));
                            purchaseTimer.start();
                        } catch (Exception error) {
                            status.setText("Open the checkout link failed: " + error.getMessage());
                        }
                    });
                } catch (Exception error) {
                    SwingUtilities.invokeLater(() -> status.setText(error.getMessage()));
                }
            });
        }

        private void pollPurchase() {
            if (orderId == null || closing || checkingPurchase) return;
            checkingPurchase = true;
            final String checking = orderId;
            NETWORK.execute(() -> {
                try {
                    String path = "/api/purchase/" + URLEncoder.encode(checking, "UTF-8");
                    Map<String, Object> result = object(new JsonParser(request("GET", path, null)).parse());
                    String state = (String) result.get("state");
                    int newBalance = ((Number) result.get("balance")).intValue();
                    SwingUtilities.invokeLater(() -> {
                        checkingPurchase = false;
                        if (!checking.equals(orderId)) return;
                        balance = newBalance;
                        if ("COMPLETED".equals(state)) {
                            orderId = null;
                            purchaseTimer.stop();
                            status.setText("Payment confirmed. " + result.get("coins") + " coins added.");
                        } else if ("FAILED".equals(state)) {
                            orderId = null;
                            purchaseTimer.stop();
                            status.setText("Payment not completed; no coins were added.");
                        }
                        game.repaint();
                    });
                } catch (Exception error) {
                    SwingUtilities.invokeLater(() -> {
                        checkingPurchase = false;
                        status.setText("Payment status check failed: " + error.getMessage());
                    });
                }
            });
        }

        private void saveRun(String mode, int score, int coins) {
            NETWORK.execute(() -> {
                try {
                    String body = "{\"mode\":" + jsonString(mode) + ",\"score\":" + score + ",\"coins\":" + coins + "}";
                    Map<String, Object> result = object(new JsonParser(request("POST", "/api/run", body)).parse());
                    balance = ((Number) result.get("balance")).intValue();
                    best = ((Number) result.get("best")).intValue();
                    SwingUtilities.invokeLater(() -> game.repaint());
                } catch (Exception error) {
                    SwingUtilities.invokeLater(() -> status.setText("Could not save this run: " + error.getMessage()));
                }
            });
        }
    }

    private static final class GamePanel extends JPanel {
        private final List<Pipe> pipes = new ArrayList<Pipe>();
        private final List<Coin> coins = new ArrayList<Coin>();
        private final List<Particle> particles = new ArrayList<Particle>();
        private final Random random = new Random();
        private Mode mode;
        private String skin = "Sunny";
        private String state = "intro";
        private double birdY = 300;
        private double velocity;
        private double elapsed;
        private double spawn;
        private long previous = System.nanoTime();
        private int score;
        private int runCoins;
        private boolean saved;
        private Runnable onStats = () -> {};
        private final Timer timer;

        GamePanel() {
            setPreferredSize(new Dimension(480, 640));
            setMinimumSize(new Dimension(360, 480));
            setFocusable(true);
            addMouseListener(new java.awt.event.MouseAdapter() {
                public void mousePressed(java.awt.event.MouseEvent event) { flap(); }
            });
            addKeyListener(new java.awt.event.KeyAdapter() {
                public void keyPressed(java.awt.event.KeyEvent event) {
                    if (event.getKeyCode() == java.awt.event.KeyEvent.VK_SPACE
                            || event.getKeyCode() == java.awt.event.KeyEvent.VK_UP) flap();
                }
            });
            timer = new Timer(16, event -> tick());
            timer.start();
        }

        void setOnStats(Runnable callback) { onStats = callback; }
        void setMode(Mode value) {
            mode = value;
            if ("playing".equals(state)) state = "ready";
            score = 0;
            runCoins = 0;
            repaint();
        }
        void setSkin(String value) { if (value != null && SKINS.containsKey(value)) skin = value; repaint(); }

        private void flap() {
            if (!isFocusOwner()) requestFocusInWindow();
            if ("intro".equals(state) || "ready".equals(state) || "over".equals(state)) {
                start();
            } else if (mode != null) {
                velocity = mode.flap;
            }
        }

        private void start() {
            if (mode == null) return;
            state = "playing";
            score = 0;
            runCoins = 0;
            birdY = getHeight() * 0.47;
            velocity = mode.flap;
            pipes.clear();
            coins.clear();
            particles.clear();
            spawn = 0.35;
            saved = false;
            onStats.run();
        }

        private void addPipe(int width, int height) {
            int gap = mode.gap;
            double low = gap / 2.0 + 55;
            double high = height - 34 - gap / 2.0 - 55;
            double center = low + random.nextDouble() * Math.max(1, high - low);
            double x = width + 15;
            pipes.add(new Pipe(x, center));
            coins.add(new Coin(x + 110, center + (random.nextDouble() - 0.5) * gap * 0.35));
        }

        private void tick() {
            long now = System.nanoTime();
            double dt = Math.min((now - previous) / 1_000_000_000.0, 0.04);
            previous = now;
            elapsed += dt;
            if ("intro".equals(state) && elapsed > 1.0) state = "ready";
            if ("playing".equals(state) && mode != null) updateGame(dt);
            onStats.run();
            repaint();
        }

        private void updateGame(double dt) {
            int height = getHeight();
            int width = getWidth();
            birdY += velocity * dt;
            velocity += mode.gravity * dt;
            spawn -= dt;
            if (spawn <= 0) {
                addPipe(width, height);
                spawn = mode.interval;
            }
            double speed = mode.speed + Math.min(score * 2.2, 70);
            for (Pipe pipe : pipes) {
                pipe.x -= speed * dt;
                if (!pipe.scored && pipe.x + 68 < 118) {
                    pipe.scored = true;
                    score++;
                }
                if (pipe.x < 153 && pipe.x + 72 > 83
                        && (birdY - 15 < pipe.center - mode.gap / 2.0
                        || birdY + 15 > pipe.center + mode.gap / 2.0)) {
                    endRun();
                    break;
                }
            }
            for (Coin coin : coins) {
                coin.x -= speed * dt;
                if (!coin.collected && Math.hypot(118 - coin.x, birdY - coin.y) < 34) {
                    coin.collected = true;
                    runCoins += "fun".equals(mode.id) ? 2 : 1;
                    score += 2;
                    for (int i = 0; i < 10; i++) particles.add(new Particle(coin.x, coin.y, random));
                }
            }
            pipes.removeIf(pipe -> pipe.x + 80 < 0);
            coins.removeIf(coin -> coin.x < -25);
            particles.removeIf(particle -> particle.life <= 0);
            for (Particle particle : particles) particle.step(dt);
            if (birdY < 15 || birdY > height - 49) endRun();
        }

        private void endRun() {
            if (!"playing".equals(state)) return;
            state = "over";
            if (!saved && mode != null) {
                saved = true;
                JFrame frame = (JFrame) SwingUtilities.getWindowAncestor(this);
                if (frame instanceof GameWindow) ((GameWindow) frame).saveRun(mode.id, score, runCoins);
            }
        }

        protected void paintComponent(Graphics graphics) {
            super.paintComponent(graphics);
            Graphics2D g = (Graphics2D) graphics.create();
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            int width = getWidth();
            int height = getHeight();
            Color[] colors = SKINS.get(skin);
            g.setPaint(new GradientPaint(0, 0, colors[0], 0, height, colors[1]));
            g.fillRect(0, 0, width, height);
            drawScenery(g, width, height, colors);
            if (mode != null) {
                for (Pipe pipe : pipes) drawPipe(g, pipe, height, colors);
                for (Coin coin : coins) if (!coin.collected) drawCoin(g, coin, colors[5]);
            }
            for (Particle particle : particles) {
                g.setColor(colors[5]);
                g.fill(new Ellipse2D.Double(particle.x - 3, particle.y - 3, 6, 6));
            }
            drawBird(g, colors);
            if (!"playing".equals(state)) drawMessage(g, width, height);
            else {
                g.setColor(Color.WHITE);
                g.setFont(new Font("SansSerif", Font.BOLD, 25));
                g.drawString(Integer.toString(score), width / 2 - 8, 48);
            }
            g.dispose();
        }

        private void drawScenery(Graphics2D g, int width, int height, Color[] c) {
            if ("Midnight".equals(skin) || "Spooky".equals(skin) || "horror".equals(mode == null ? "" : mode.id)) {
                Random stars = new Random(23);
                g.setColor(new Color(255, 255, 255, 165));
                for (int i = 0; i < 55; i++) {
                    int x = stars.nextInt(Math.max(width, 1));
                    int y = stars.nextInt(Math.max(height - 90, 1));
                    g.fillOval(x, y, 2, 2);
                }
            } else {
                g.setColor(new Color(255, 255, 255, 145));
                int drift = (int) (elapsed * 16) % (width + 90);
                for (int base : new int[]{40, 260, 440}) {
                    int x = Math.floorMod(base - drift, width + 90) - 30;
                    int y = base == 260 ? 190 : base == 440 ? 70 : 110;
                    g.fillOval(x, y, 65, 24);
                    g.fillOval(x + 14, y - 12, 33, 30);
                }
            }
            g.setColor(c[1]);
            g.fillOval(-90, height - 180, width / 2 + 120, 130);
            g.fillOval(width / 3, height - 150, width, 115);
            g.setColor(c[2]);
            g.fillRect(0, height - 34, width, 34);
            g.setColor(c[1].brighter());
            g.fillRect(0, height - 34, width, 6);
            if ("horror".equals(mode == null ? "" : mode.id)) {
                g.setColor(new Color(24, 10, 35, 38));
                g.fillRect(0, 0, width, height);
            }
        }

        private void drawPipe(Graphics2D g, Pipe pipe, int height, Color[] c) {
            double gap = mode.gap;
            double top = pipe.center - gap / 2.0;
            double bottom = pipe.center + gap / 2.0;
            int x = (int) pipe.x;
            g.setPaint(new GradientPaint(x, 0, c[3].brighter(), x + 72, 0, c[3].darker()));
            g.fillRect(x + 5, 0, 62, (int) top);
            g.fillRect(x + 5, (int) bottom, 62, Math.max(0, height - 34 - (int) bottom));
            g.fillRect(x, (int) top - 20, 72, 22);
            g.fillRect(x, (int) bottom, 72, 22);
            g.setColor(new Color(20, 38, 48, 180));
            g.setStroke(new BasicStroke(2));
            g.drawRect(x + 5, 0, 62, (int) top);
            g.drawRect(x + 5, (int) bottom, 62, Math.max(0, height - 34 - (int) bottom));
            g.drawRoundRect(x, (int) top - 20, 72, 22, 7, 7);
            g.drawRoundRect(x, (int) bottom, 72, 22, 7, 7);
            g.setColor(new Color(255, 255, 255, 65));
            g.fillRect(x + 15, 2, 7, Math.max(0, (int) top - 22));
            g.fillRect(x + 15, (int) bottom + 24, 7, Math.max(0, height - 58 - (int) bottom));
        }

        private void drawCoin(Graphics2D g, Coin coin, Color color) {
            int x = (int) coin.x;
            int y = (int) coin.y;
            g.setColor(new Color(0, 0, 0, 45));
            g.fillOval(x - 15, y - 12, 32, 32);
            g.setColor(color);
            g.fillOval(x - 16, y - 16, 32, 32);
            g.setColor(new Color(164, 109, 25));
            g.setStroke(new BasicStroke(3));
            g.drawOval(x - 16, y - 16, 32, 32);
            g.setColor(Color.WHITE);
            g.setFont(new Font("SansSerif", Font.BOLD, 16));
            g.drawString("$", x - 5, y + 6);
        }

        private void drawBird(Graphics2D g, Color[] c) {
            double y = birdY + ("playing".equals(state) ? 0 : Math.sin(elapsed * 4) * 4);
            int x = 118;
            int wing = (int) (Math.sin(elapsed * 18) * 4);
            g.setColor(c[3].darker());
            g.fillPolygon(new int[]{x - 12, x - 28, x - 23}, new int[]{(int) y + 5, (int) y - 2, (int) y + 14}, 3);
            g.setColor(c[4]);
            g.fill(new Ellipse2D.Double(x - 20, y - 19, 40, 38));
            g.setColor(new Color(170, 125, 50));
            g.draw(new Ellipse2D.Double(x - 20, y - 19, 40, 38));
            g.setColor(new Color(255, 245, 196));
            g.fill(new Ellipse2D.Double(x - 12, y + wing, 18, 12));
            g.setColor(Color.WHITE);
            g.fillOval(x + 2, (int) y - 11, 14, 14);
            g.setColor(new Color(38, 56, 84));
            g.fillOval(x + 9, (int) y - 7, 5, 6);
            g.setColor(new Color(242, 140, 69));
            g.fillPolygon(new int[]{x + 15, x + 31, x + 15}, new int[]{(int) y + 1, (int) y + 6, (int) y + 11}, 3);
        }

        private void drawMessage(Graphics2D g, int width, int height) {
            String title = "intro".equals(state) ? "FLAPPY FRIENDS" :
                    "over".equals(state) ? "Nice try!" : "Ready to fly?";
            String subtitle = "over".equals(state)
                    ? "Score " + score + "  ·  Coins " + runCoins + "  ·  Click to retry"
                    : "Click or press Space to flap";
            int alpha = Math.min(255, 130 + (int) (125 * Math.abs(Math.sin(elapsed * 2))));
            g.setColor(new Color(25, 45, 70, alpha));
            g.setFont(new Font("SansSerif", Font.BOLD, 31));
            int titleWidth = g.getFontMetrics().stringWidth(title);
            g.drawString(title, (width - titleWidth) / 2, (int) (height * 0.39));
            g.setFont(new Font("SansSerif", Font.BOLD, 15));
            int subtitleWidth = g.getFontMetrics().stringWidth(subtitle);
            g.drawString(subtitle, (width - subtitleWidth) / 2, (int) (height * 0.39) + 35);
        }
    }

    private static final class Pipe {
        double x;
        final double center;
        boolean scored;
        Pipe(double x, double center) { this.x = x; this.center = center; }
    }

    private static final class Coin {
        double x;
        final double y;
        boolean collected;
        Coin(double x, double y) { this.x = x; this.y = y; }
    }

    private static final class Particle {
        double x;
        double y;
        final double vx;
        final double vy;
        double life = 0.45;
        Particle(double x, double y, Random random) {
            this.x = x;
            this.y = y;
            this.vx = random.nextDouble() * 130 - 65;
            this.vy = random.nextDouble() * 125 - 95;
        }
        void step(double dt) {
            x += vx * dt;
            y += vy * dt;
            life -= dt;
        }
    }

    private static final class JsonParser {
        private final String text;
        private int index;
        JsonParser(String text) { this.text = text; }

        Object parse() {
            Object value = parseValue();
            whitespace();
            if (index != text.length()) throw new IllegalArgumentException("Invalid JSON response.");
            return value;
        }

        private Object parseValue() {
            whitespace();
            if (index >= text.length()) throw new IllegalArgumentException("Empty JSON response.");
            char current = text.charAt(index);
            if (current == '{') return parseObject();
            if (current == '[') return parseArray();
            if (current == '"') return parseString();
            if (current == 't' && word("true")) return Boolean.TRUE;
            if (current == 'f' && word("false")) return Boolean.FALSE;
            if (current == 'n' && word("null")) return null;
            return parseNumber();
        }

        private Map<String, Object> parseObject() {
            Map<String, Object> result = new LinkedHashMap<String, Object>();
            index++;
            whitespace();
            if (take('}')) return result;
            do {
                whitespace();
                String key = parseString();
                whitespace();
                require(':');
                result.put(key, parseValue());
                whitespace();
                if (take('}')) return result;
                require(',');
            } while (true);
        }

        private List<Object> parseArray() {
            List<Object> result = new ArrayList<Object>();
            index++;
            whitespace();
            if (take(']')) return result;
            do {
                result.add(parseValue());
                whitespace();
                if (take(']')) return result;
                require(',');
            } while (true);
        }

        private String parseString() {
            require('"');
            StringBuilder result = new StringBuilder();
            while (index < text.length()) {
                char ch = text.charAt(index++);
                if (ch == '"') return result.toString();
                if (ch == '\\') {
                    if (index >= text.length()) break;
                    char escaped = text.charAt(index++);
                    if (escaped == 'u') {
                        if (index + 4 > text.length()) break;
                        result.append((char) Integer.parseInt(text.substring(index, index + 4), 16));
                        index += 4;
                    } else if (escaped == 'n') result.append('\n');
                    else if (escaped == 'r') result.append('\r');
                    else if (escaped == 't') result.append('\t');
                    else result.append(escaped);
                } else result.append(ch);
            }
            throw new IllegalArgumentException("Unterminated JSON string.");
        }

        private Number parseNumber() {
            int start = index;
            while (index < text.length() && "-+0123456789.eE".indexOf(text.charAt(index)) >= 0) index++;
            if (start == index) throw new IllegalArgumentException("Invalid JSON value.");
            String value = text.substring(start, index);
            return value.indexOf('.') >= 0 || value.indexOf('e') >= 0 || value.indexOf('E') >= 0
                    ? Double.valueOf(value) : Long.valueOf(value);
        }

        private boolean word(String value) {
            if (!text.startsWith(value, index)) return false;
            index += value.length();
            return true;
        }
        private void whitespace() {
            while (index < text.length() && Character.isWhitespace(text.charAt(index))) index++;
        }
        private boolean take(char ch) {
            if (index < text.length() && text.charAt(index) == ch) { index++; return true; }
            return false;
        }
        private void require(char ch) {
            if (!take(ch)) throw new IllegalArgumentException("Invalid JSON response.");
        }
    }
}