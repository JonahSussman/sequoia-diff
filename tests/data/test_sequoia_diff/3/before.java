package net.jsussman.ioedict;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;

public class App {
  public static void main(String[] args) {
    System.out.println("Starting application!");

    try (FileInputStream in = new FileInputStream("input.txt");
        FileOutputStream out = new FileOutputStream("output.txt")) {

      int c;
      while ((c = in.read()) != -1) {
        out.write(c);
      }
    } catch (IOException e) {
      e.printStackTrace();
    }
  }
}
